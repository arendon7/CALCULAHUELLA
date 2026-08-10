from __future__ import annotations

from io import BytesIO

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import add_audit, get_db
from .db.models import BenchmarkReference, ImpactSnapshot, Organization
from .impact_intelligence import compare_benchmarks, impact_metrics, portfolio_comparison, refresh_impact_snapshot


def _require_impact_view(user: dict[str, object]) -> None:
    capabilities = user.get("capabilities", set())
    if "view_impact" not in capabilities and "manage_impact" not in capabilities:
        raise HTTPException(403, "Tu rol no tiene acceso a inteligencia de impacto")


def register_impact_intelligence_routes(
    app, templates, common_context, require_user, ensure_capability, set_flash
) -> None:
    @app.get("/inteligencia-impacto", response_class=HTMLResponse)
    def impact_intelligence_page(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        _require_impact_view(user)
        organization_id = int(user["organization_id"])
        metrics = impact_metrics(session, organization_id)
        snapshot = session.scalar(
            select(ImpactSnapshot).where(ImpactSnapshot.organization_id == organization_id).order_by(ImpactSnapshot.calculated_at.desc())
        )
        if not snapshot:
            snapshot = refresh_impact_snapshot(session, organization_id, created_by=str(user["email"]))
            session.commit()
        references = list(session.scalars(
            select(BenchmarkReference).where(BenchmarkReference.organization_id == organization_id, BenchmarkReference.status == "Activo").order_by(BenchmarkReference.metric_name)
        ))
        comparisons = compare_benchmarks(metrics, references)
        history = list(session.scalars(
            select(ImpactSnapshot).where(ImpactSnapshot.organization_id == organization_id).order_by(ImpactSnapshot.calculated_at.desc()).limit(12)
        ))
        organization_ids = [int(item["id"]) for item in user.get("organizations", [])]
        portfolio = portfolio_comparison(session, organization_ids or [organization_id], organization_id)
        return templates.TemplateResponse(
            request=request, name="impact_intelligence.html",
            context=common_context(request, session, user, "impact", metrics=metrics, snapshot=snapshot, references=references, comparisons=comparisons, history=history, portfolio=portfolio),
        )

    @app.post("/inteligencia-impacto/recalcular")
    def recalculate_impact(request: Request, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_impact")
        snapshot = refresh_impact_snapshot(session, int(user["organization_id"]), created_by=str(user["email"]))
        add_audit(session, int(user["organization_id"]), str(user["email"]), "RECALCULAR", "Analítica de impacto", str(snapshot.id), new_value=f"Puntaje {snapshot.impact_score}/100")
        session.commit()
        set_flash(request, "Analítica de impacto actualizada.")
        return RedirectResponse("/inteligencia-impacto", status_code=303)

    @app.post("/inteligencia-impacto/benchmarks/nuevo")
    def create_benchmark(
        request: Request, name: str = Form(...), metric_code: str = Form(...), metric_name: str = Form(...),
        period_label: str = Form("Referencia"), unit: str = Form(...), median_value: float = Form(...),
        top_quartile_value: float = Form(...), lower_is_better: str = Form("true"), source_type: str = Form("Referencia interna"),
        source_reference: str = Form(""), confidence_level: str = Form("Media"), notes: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_impact")
        allowed_metrics = {"intensity_employee", "intensity_revenue_billion", "intensity_production", "quality_score", "evidence_coverage"}
        if metric_code not in allowed_metrics or median_value < 0 or top_quartile_value < 0:
            raise HTTPException(400, "Métrica o valores de referencia inválidos")
        org = session.get(Organization, int(user["organization_id"]))
        reference = BenchmarkReference(
            organization_id=org.id, name=name.strip(), sector=org.sector, metric_code=metric_code, metric_name=metric_name.strip(),
            period_label=period_label.strip(), unit=unit.strip(), median_value=median_value, top_quartile_value=top_quartile_value,
            lower_is_better=lower_is_better.lower() in {"1", "true", "si", "sí", "on"}, source_type=source_type.strip(),
            source_reference=source_reference.strip(), confidence_level=confidence_level, notes=notes.strip(), created_by=str(user["email"]),
        )
        session.add(reference)
        add_audit(session, org.id, str(user["email"]), "CREAR", "Benchmark", reference.name, f"{metric_name}: mediana {median_value}; cuartil {top_quartile_value}")
        session.commit()
        set_flash(request, "Referencia de benchmark registrada.")
        return RedirectResponse("/inteligencia-impacto", status_code=303)

    @app.post("/inteligencia-impacto/benchmarks/{reference_id}/estado")
    def update_benchmark_status(reference_id: int, request: Request, status: str = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "manage_impact")
        reference = session.scalar(select(BenchmarkReference).where(BenchmarkReference.id == reference_id, BenchmarkReference.organization_id == int(user["organization_id"])))
        if not reference:
            raise HTTPException(404, "Benchmark no encontrado")
        if status not in {"Activo", "Archivado"}:
            raise HTTPException(400, "Estado inválido")
        reference.status = status
        add_audit(session, reference.organization_id, str(user["email"]), "ACTUALIZAR", "Benchmark", reference.name, new_value=status)
        session.commit()
        set_flash(request, "Estado del benchmark actualizado.")
        return RedirectResponse("/inteligencia-impacto", status_code=303)

    @app.get("/inteligencia-impacto/exportar.xlsx")
    def export_impact_intelligence(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        _require_impact_view(user)
        organization_id = int(user["organization_id"])
        metrics = impact_metrics(session, organization_id)
        references = list(session.scalars(select(BenchmarkReference).where(BenchmarkReference.organization_id == organization_id)))
        comparisons = compare_benchmarks(metrics, references)
        wb = Workbook()
        ws = wb.active
        ws.title = "Resumen de impacto"
        ws.append(["Métrica", "Valor", "Unidad"])
        units = {"total_emissions": "tCO2e", "intensity_employee": "tCO2e/empleado", "intensity_revenue_billion": "tCO2e/mil millones COP", "quality_score": "%", "evidence_coverage": "%", "expected_reduction": "tCO2e", "annual_savings": "COP/año", "value_per_tonne": "COP/tCO2e"}
        for key in ["total_emissions", "intensity_employee", "intensity_revenue_billion", "quality_score", "evidence_coverage", "expected_reduction", "annual_savings", "value_per_tonne"]:
            ws.append([key, metrics.get(key, 0), units[key]])
        ws2 = wb.create_sheet("Benchmark")
        ws2.append(["Referencia", "Métrica", "Actual", "Mediana", "Cuartil superior", "Unidad", "Estado", "Fuente", "Confianza"])
        for row in comparisons:
            ref = row["reference"]
            ws2.append([ref.name, ref.metric_name, row["current"], ref.median_value, ref.top_quartile_value, ref.unit, row["status"], ref.source_reference, ref.confidence_level])
        buffer = BytesIO()
        wb.save(buffer)
        filename = f"inteligencia_impacto_{organization_id}.xlsx"
        return Response(content=buffer.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
