from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import (
    AssuranceEngagement, AssuranceFinding, MitigationMonitoringPeriod, MitigationProject,
    ProductFootprintStudy, ProductLifeCycleStage, add_audit, get_db,
)
from .product_project_assurance import (
    ACCOUNTING_TYPES, ASSURANCE_LEVELS, ASSURANCE_SUBJECTS, LIFECYCLE_STAGES,
    PRODUCT_BOUNDARIES, PROJECT_TYPES, assurance_readiness, assurance_summary,
    calculate_product_stage, calculate_project_reduction, product_summary, project_readiness, project_summary,
)


def register_product_project_assurance_routes(app, templates, common_context, require_user, ensure_capability, set_flash, get_inventory, ensure_inventory_editable):
    @app.get("/huella-producto", response_class=HTMLResponse)
    def product_page(request: Request, study_id: int | None = None, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not ({"view_methodology", "review", "approve"} & set(user.get("capabilities") or set())):
            raise HTTPException(403, "Tu rol no puede consultar huellas de producto")
        inventory = get_inventory(session, user)
        studies = list(session.scalars(select(ProductFootprintStudy).where(ProductFootprintStudy.inventory_id == inventory.id).options(selectinload(ProductFootprintStudy.stages)).order_by(ProductFootprintStudy.created_at.desc())))
        selected = next((x for x in studies if x.id == study_id), studies[0] if studies else None)
        summaries = {x.id: product_summary(x) for x in studies}
        return templates.TemplateResponse(request=request, name="product_footprint.html", context=common_context(
            request, session, user, "product_footprint", inventory=inventory, studies=studies, selected=selected, summaries=summaries,
            boundaries=PRODUCT_BOUNDARIES, lifecycle_stages=LIFECYCLE_STAGES, accounting_types=ACCOUNTING_TYPES,
        ))

    @app.post("/huella-producto/nueva")
    def create_product_study(
        request: Request, product_name: str = Form(...), product_code: str = Form(""), declared_unit: str = Form(...), reference_flow: float = Form(1),
        boundary: str = Form("De la cuna a la puerta"), methodology: str = Form("ISO 14067:2018"), pcr_reference: str = Form(""),
        allocation_method: str = Form("Sin asignación"), cutoff_rule_percent: float = Form(1), biogenic_treatment: str = Form("Reporte separado"),
        land_use_included: str | None = Form(None), data_quality_rating: str = Form("C"), notes: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        inventory = get_inventory(session, user); ensure_inventory_editable(inventory)
        if reference_flow <= 0 or not product_name.strip() or not declared_unit.strip():
            set_flash(request, "Producto, unidad declarada y flujo de referencia válido son obligatorios.", "error")
            return RedirectResponse("/huella-producto#nueva", status_code=303)
        study = ProductFootprintStudy(
            inventory_id=inventory.id, product_name=product_name.strip(), product_code=product_code.strip(), declared_unit=declared_unit.strip(),
            reference_flow=reference_flow, boundary=boundary if boundary in PRODUCT_BOUNDARIES else PRODUCT_BOUNDARIES[0], methodology=methodology.strip(),
            pcr_reference=pcr_reference.strip(), allocation_method=allocation_method.strip(), cutoff_rule_percent=max(0, min(cutoff_rule_percent, 100)),
            biogenic_treatment=biogenic_treatment.strip(), land_use_included=land_use_included is not None, data_quality_rating=data_quality_rating,
            notes=notes.strip(), created_by=str(user["email"]),
        )
        session.add(study); session.flush()
        add_audit(session, int(user["organization_id"]), str(user["email"]), "CREAR", "Estudio de huella de producto", study.product_name, new_value=f"{study.boundary} · {study.declared_unit}")
        session.commit(); set_flash(request, "Estudio creado. Agrega las etapas del ciclo de vida.")
        return RedirectResponse(f"/huella-producto?study_id={study.id}", status_code=303)

    @app.post("/huella-producto/{study_id}/etapas")
    def add_product_stage(
        study_id: int, request: Request, stage_code: str = Form(...), accounting_type: str = Form("Emisión"), activity_name: str = Form(...),
        activity_value: float = Form(...), activity_unit: str = Form(...), factor_value: float = Form(...), factor_output_unit: str = Form("kg CO2e"),
        data_source: str = Form(...), geography: str = Form(""), reference_year: int = Form(0), uncertainty_percentage: float = Form(0),
        evidence_reference: str = Form(""), excluded: str | None = Form(None), exclusion_reason: str = Form(""),
        session: Session = Depends(get_db), user: dict = Depends(require_user),
    ):
        ensure_capability(user, "manage_methodology_governance")
        inventory = get_inventory(session, user); ensure_inventory_editable(inventory)
        study = session.scalar(select(ProductFootprintStudy).where(ProductFootprintStudy.id == study_id, ProductFootprintStudy.inventory_id == inventory.id))
        if not study: raise HTTPException(404, "Estudio no encontrado")
        if study.status == "Aprobado": raise HTTPException(409, "El estudio aprobado no admite cambios")
        stage_map = dict(LIFECYCLE_STAGES)
        if stage_code not in stage_map or accounting_type not in ACCOUNTING_TYPES: raise HTTPException(400, "Etapa o tipo contable inválido")
        is_excluded = excluded is not None
        if is_excluded and not exclusion_reason.strip():
            set_flash(request, "Toda exclusión debe justificarse.", "error"); return RedirectResponse(f"/huella-producto?study_id={study.id}#etapas", status_code=303)
        try: calculated = 0.0 if is_excluded else calculate_product_stage(activity_value, factor_value, factor_output_unit)
        except ValueError as exc:
            set_flash(request, str(exc), "error"); return RedirectResponse(f"/huella-producto?study_id={study.id}#etapas", status_code=303)
        item = ProductLifeCycleStage(
            study_id=study.id, stage_code=stage_code, stage_name=stage_map[stage_code], accounting_type=accounting_type,
            activity_name=activity_name.strip(), activity_value=activity_value, activity_unit=activity_unit.strip(), factor_value=factor_value,
            factor_output_unit=factor_output_unit.strip(), calculated_tco2e=calculated, data_source=data_source.strip(), geography=geography.strip(),
            reference_year=max(reference_year, 0), uncertainty_percentage=max(0, min(uncertainty_percentage, 100)), evidence_reference=evidence_reference.strip(),
            excluded=is_excluded, exclusion_reason=exclusion_reason.strip(), created_by=str(user["email"]),
        )
        session.add(item); add_audit(session, int(user["organization_id"]), str(user["email"]), "AGREGAR", "Etapa de ciclo de vida", item.activity_name, new_value=f"{accounting_type} · {calculated:.9f} tCO2e")
        session.commit(); set_flash(request, "Etapa agregada con trazabilidad del cálculo.")
        return RedirectResponse(f"/huella-producto?study_id={study.id}#etapas", status_code=303)

    @app.post("/huella-producto/{study_id}/revisar")
    def review_product(study_id: int, request: Request, status: str = Form(...), session: Session = Depends(get_db), user: dict = Depends(require_user)):
        ensure_capability(user, "review")
        inventory = get_inventory(session, user)
        study = session.scalar(select(ProductFootprintStudy).where(ProductFootprintStudy.id == study_id, ProductFootprintStudy.inventory_id == inventory.id).options(selectinload(ProductFootprintStudy.stages)))
        if not study: raise HTTPException(404, "Estudio no encontrado")
        if status not in {"Borrador", "En revisión", "Aprobado", "Rechazado"}: raise HTTPException(400, "Estado inválido")
        summary = product_summary(study)
        if status == "Aprobado" and (summary["blockers"] or not study.stages):
            set_flash(request, "No puede aprobarse: " + " ".join(summary["blockers"] or ["no hay etapas registradas."]), "error")
            return RedirectResponse(f"/huella-producto?study_id={study.id}", status_code=303)
        previous=study.status; study.status=status; study.reviewed_by=str(user["email"]); study.reviewed_at=datetime.now(UTC)
        add_audit(session, int(user["organization_id"]), str(user["email"]), "REVISAR", "Estudio de huella de producto", study.product_name, previous_value=previous, new_value=status)
        session.commit(); set_flash(request, "Estado del estudio actualizado.")
        return RedirectResponse(f"/huella-producto?study_id={study.id}", status_code=303)

    @app.get("/api/huella-producto")
    def product_api(session: Session = Depends(get_db), user: dict = Depends(require_user)):
        inventory=get_inventory(session,user); studies=list(session.scalars(select(ProductFootprintStudy).where(ProductFootprintStudy.inventory_id==inventory.id).options(selectinload(ProductFootprintStudy.stages))))
        return {"inventory_id":inventory.id,"studies":[{"id":s.id,"product":s.product_name,"status":s.status,"summary":product_summary(s)} for s in studies]}

    @app.get("/proyectos-mitigacion", response_class=HTMLResponse)
    def project_page(request: Request, project_id: int | None = None, session: Session = Depends(get_db), user: dict = Depends(require_user)):
        if not ({"view_methodology", "review", "approve"} & set(user.get("capabilities") or set())): raise HTTPException(403, "Tu rol no puede consultar proyectos")
        inventory=get_inventory(session,user)
        projects=list(session.scalars(select(MitigationProject).where(MitigationProject.inventory_id==inventory.id).options(selectinload(MitigationProject.monitoring_periods)).order_by(MitigationProject.created_at.desc())))
        selected=next((x for x in projects if x.id==project_id), projects[0] if projects else None)
        summaries={x.id:project_summary(x) for x in projects}
        return templates.TemplateResponse(request=request,name="mitigation_projects.html",context=common_context(request,session,user,"mitigation_projects",inventory=inventory,projects=projects,selected=selected,summaries=summaries,project_types=PROJECT_TYPES))

    @app.post("/proyectos-mitigacion/nuevo")
    def create_project(
        request: Request, name: str=Form(...), project_type: str=Form("Reducción de emisiones"), methodology: str=Form("ISO 14064-2:2019"),
        baseline_scenario: str=Form(...), project_scenario: str=Form(...), additionality_basis: str=Form(""), monitoring_plan: str=Form(""),
        leakage_sources: str=Form(""), ownership_statement: str=Form(""), double_counting_control: str=Form(""), start_date: date=Form(...), end_date: date=Form(...),
        estimated_baseline_tco2e: float=Form(0), estimated_project_tco2e: float=Form(0), estimated_leakage_tco2e: float=Form(0), estimated_removals_tco2e: float=Form(0),
        session: Session=Depends(get_db), user: dict=Depends(require_user),
    ):
        ensure_capability(user,"manage_methodology_governance"); inventory=get_inventory(session,user); ensure_inventory_editable(inventory)
        if end_date < start_date: set_flash(request,"La fecha final no puede ser anterior a la inicial.","error"); return RedirectResponse("/proyectos-mitigacion#nuevo",status_code=303)
        try: reduction=calculate_project_reduction(estimated_baseline_tco2e,estimated_project_tco2e,estimated_leakage_tco2e,estimated_removals_tco2e)
        except ValueError as exc: set_flash(request,str(exc),"error"); return RedirectResponse("/proyectos-mitigacion#nuevo",status_code=303)
        project=MitigationProject(inventory_id=inventory.id,name=name.strip(),project_type=project_type,methodology=methodology.strip(),baseline_scenario=baseline_scenario.strip(),project_scenario=project_scenario.strip(),additionality_basis=additionality_basis.strip(),monitoring_plan=monitoring_plan.strip(),leakage_sources=leakage_sources.strip(),ownership_statement=ownership_statement.strip(),double_counting_control=double_counting_control.strip(),start_date=start_date,end_date=end_date,estimated_baseline_tco2e=estimated_baseline_tco2e,estimated_project_tco2e=estimated_project_tco2e,estimated_leakage_tco2e=estimated_leakage_tco2e,estimated_removals_tco2e=estimated_removals_tco2e,estimated_reduction_tco2e=reduction,created_by=str(user["email"]))
        session.add(project); session.flush(); add_audit(session,int(user["organization_id"]),str(user["email"]),"CREAR","Proyecto de mitigación",project.name,new_value=f"Reducción estimada {reduction:.6f} tCO2e")
        session.commit(); set_flash(request,"Proyecto creado como expediente separado del inventario.")
        return RedirectResponse(f"/proyectos-mitigacion?project_id={project.id}",status_code=303)

    @app.post("/proyectos-mitigacion/{project_id}/monitoreo")
    def add_monitoring(project_id:int,request:Request,period_start:date=Form(...),period_end:date=Form(...),baseline_tco2e:float=Form(...),project_tco2e:float=Form(...),leakage_tco2e:float=Form(0),removals_tco2e:float=Form(0),uncertainty_percentage:float=Form(0),evidence_reference:str=Form(...),notes:str=Form(""),session:Session=Depends(get_db),user:dict=Depends(require_user)):
        ensure_capability(user,"manage_methodology_governance"); inventory=get_inventory(session,user); ensure_inventory_editable(inventory)
        project=session.scalar(select(MitigationProject).where(MitigationProject.id==project_id,MitigationProject.inventory_id==inventory.id))
        if not project: raise HTTPException(404,"Proyecto no encontrado")
        if period_end<period_start: set_flash(request,"Periodo de monitoreo inválido.","error"); return RedirectResponse(f"/proyectos-mitigacion?project_id={project.id}#monitoreo",status_code=303)
        try: reduction=calculate_project_reduction(baseline_tco2e,project_tco2e,leakage_tco2e,removals_tco2e)
        except ValueError as exc: set_flash(request,str(exc),"error"); return RedirectResponse(f"/proyectos-mitigacion?project_id={project.id}#monitoreo",status_code=303)
        item=MitigationMonitoringPeriod(project_id=project.id,period_start=period_start,period_end=period_end,baseline_tco2e=baseline_tco2e,project_tco2e=project_tco2e,leakage_tco2e=leakage_tco2e,removals_tco2e=removals_tco2e,reduction_tco2e=reduction,uncertainty_percentage=max(0,min(uncertainty_percentage,100)),evidence_reference=evidence_reference.strip(),notes=notes.strip(),created_by=str(user["email"]))
        session.add(item); add_audit(session,int(user["organization_id"]),str(user["email"]),"AGREGAR","Monitoreo de mitigación",project.name,new_value=f"{period_start}/{period_end} · {reduction:.6f} tCO2e")
        session.commit(); set_flash(request,"Periodo de monitoreo registrado.")
        return RedirectResponse(f"/proyectos-mitigacion?project_id={project.id}#monitoreo",status_code=303)

    @app.post("/proyectos-mitigacion/{project_id}/revisar")
    def review_project(project_id:int,request:Request,status:str=Form(...),session:Session=Depends(get_db),user:dict=Depends(require_user)):
        ensure_capability(user,"review"); inventory=get_inventory(session,user)
        project=session.scalar(select(MitigationProject).where(MitigationProject.id==project_id,MitigationProject.inventory_id==inventory.id).options(selectinload(MitigationProject.monitoring_periods)))
        if not project: raise HTTPException(404,"Proyecto no encontrado")
        if status not in {"Diseño","En monitoreo","Aprobado","Rechazado"}: raise HTTPException(400,"Estado inválido")
        issues=project_readiness(project)
        if status=="Aprobado" and issues: set_flash(request,"No puede aprobarse: "+" ".join(issues),"error"); return RedirectResponse(f"/proyectos-mitigacion?project_id={project.id}",status_code=303)
        previous=project.status;project.status=status;project.reviewed_by=str(user["email"]);project.reviewed_at=datetime.now(UTC)
        add_audit(session,int(user["organization_id"]),str(user["email"]),"REVISAR","Proyecto de mitigación",project.name,previous_value=previous,new_value=status)
        session.commit();set_flash(request,"Estado del proyecto actualizado.");return RedirectResponse(f"/proyectos-mitigacion?project_id={project.id}",status_code=303)

    @app.post("/proyectos-mitigacion/monitoreo/{period_id}/revisar")
    def review_period(period_id:int,request:Request,status:str=Form(...),session:Session=Depends(get_db),user:dict=Depends(require_user)):
        ensure_capability(user,"review");inventory=get_inventory(session,user)
        period=session.scalar(select(MitigationMonitoringPeriod).join(MitigationProject).where(MitigationMonitoringPeriod.id==period_id,MitigationProject.inventory_id==inventory.id))
        if not period:raise HTTPException(404,"Periodo no encontrado")
        if status not in {"Borrador","En revisión","Aprobado","Rechazado"}:raise HTTPException(400,"Estado inválido")
        period.status=status;session.commit();set_flash(request,"Periodo revisado.");return RedirectResponse(f"/proyectos-mitigacion?project_id={period.project_id}#monitoreo",status_code=303)

    @app.get("/api/proyectos-mitigacion")
    def project_api(session:Session=Depends(get_db),user:dict=Depends(require_user)):
        inventory=get_inventory(session,user);projects=list(session.scalars(select(MitigationProject).where(MitigationProject.inventory_id==inventory.id).options(selectinload(MitigationProject.monitoring_periods))))
        return {"inventory_id":inventory.id,"projects":[{"id":p.id,"name":p.name,"status":p.status,"summary":project_summary(p)} for p in projects]}

    @app.get("/aseguramiento", response_class=HTMLResponse)
    def assurance_page(request:Request,engagement_id:int|None=None,session:Session=Depends(get_db),user:dict=Depends(require_user)):
        if not ({"external_audit","review","approve"}&set(user.get("capabilities") or set())):raise HTTPException(403,"Tu rol no puede consultar aseguramiento")
        inventory=get_inventory(session,user); engagements=list(session.scalars(select(AssuranceEngagement).where(AssuranceEngagement.inventory_id==inventory.id).options(selectinload(AssuranceEngagement.findings)).order_by(AssuranceEngagement.created_at.desc())))
        selected=next((x for x in engagements if x.id==engagement_id),engagements[0] if engagements else None)
        readiness={x.id:assurance_readiness(x) for x in engagements}
        return templates.TemplateResponse(request=request,name="assurance.html",context=common_context(request,session,user,"assurance",inventory=inventory,engagements=engagements,selected=selected,readiness=readiness,summary=assurance_summary(engagements),subject_types=ASSURANCE_SUBJECTS,assurance_levels=ASSURANCE_LEVELS))

    @app.post("/aseguramiento/nuevo")
    def create_engagement(request:Request,subject_type:str=Form("Inventario corporativo"),subject_reference:str=Form(""),engagement_type:str=Form("Verificación"),standard:str=Form("ISO 14064-3:2019"),assurance_level:str=Form("Limitado"),materiality_percent:float=Form(5),criteria:str=Form(...),scope:str=Form(...),verifier_organization:str=Form(...),lead_verifier:str=Form(...),independence_declaration:str=Form(...),competence_basis:str=Form(...),start_date:date=Form(...),end_date:date=Form(...),session:Session=Depends(get_db),user:dict=Depends(require_user)):
        ensure_capability(user,"external_audit");inventory=get_inventory(session,user)
        if end_date<start_date:set_flash(request,"La fecha final no puede ser anterior a la inicial.","error");return RedirectResponse("/aseguramiento#nuevo",status_code=303)
        item=AssuranceEngagement(inventory_id=inventory.id,subject_type=subject_type,subject_reference=subject_reference.strip(),engagement_type=engagement_type,standard=standard.strip(),assurance_level=assurance_level,materiality_percent=max(0,min(materiality_percent,100)),criteria=criteria.strip(),scope=scope.strip(),verifier_organization=verifier_organization.strip(),lead_verifier=lead_verifier.strip(),independence_declaration=independence_declaration.strip(),competence_basis=competence_basis.strip(),start_date=start_date,end_date=end_date,created_by=str(user["email"]))
        session.add(item);session.flush();add_audit(session,int(user["organization_id"]),str(user["email"]),"CREAR","Encargo de aseguramiento",f"{item.subject_type} {item.subject_reference}",new_value=f"{item.engagement_type} · {item.assurance_level}")
        session.commit();set_flash(request,"Encargo creado con independencia, competencia, criterios y alcance documentados.");return RedirectResponse(f"/aseguramiento?engagement_id={item.id}",status_code=303)

    @app.post("/aseguramiento/{engagement_id}/hallazgos")
    def add_assurance_finding(engagement_id:int,request:Request,area:str=Form("General"),title:str=Form(...),description:str=Form(...),severity:str=Form("Menor"),evidence_reference:str=Form(""),session:Session=Depends(get_db),user:dict=Depends(require_user)):
        ensure_capability(user,"external_audit");inventory=get_inventory(session,user)
        engagement=session.scalar(select(AssuranceEngagement).where(AssuranceEngagement.id==engagement_id,AssuranceEngagement.inventory_id==inventory.id))
        if not engagement:raise HTTPException(404,"Encargo no encontrado")
        if engagement.status=="Declaración emitida":raise HTTPException(409,"La declaración emitida no admite nuevos hallazgos")
        item=AssuranceFinding(engagement_id=engagement.id,area=area.strip(),title=title.strip(),description=description.strip(),severity=severity,evidence_reference=evidence_reference.strip(),created_by=str(user["email"]))
        session.add(item);session.commit();set_flash(request,"Hallazgo agregado al encargo.");return RedirectResponse(f"/aseguramiento?engagement_id={engagement.id}#hallazgos",status_code=303)

    @app.post("/aseguramiento/hallazgos/{finding_id}/gestionar")
    def manage_assurance_finding(finding_id:int,request:Request,status:str=Form(...),management_response:str=Form(""),verifier_conclusion:str=Form(""),session:Session=Depends(get_db),user:dict=Depends(require_user)):
        inventory=get_inventory(session,user)
        finding=session.scalar(select(AssuranceFinding).join(AssuranceEngagement).where(AssuranceFinding.id==finding_id,AssuranceEngagement.inventory_id==inventory.id))
        if not finding:raise HTTPException(404,"Hallazgo no encontrado")
        if status=="Cerrado":ensure_capability(user,"external_audit");finding.closed_at=datetime.now(UTC)
        elif not ({"review","approve","external_audit"}&set(user.get("capabilities") or set())):raise HTTPException(403,"No autorizado")
        finding.status=status;finding.management_response=management_response.strip();finding.verifier_conclusion=verifier_conclusion.strip();session.commit();set_flash(request,"Hallazgo actualizado.");return RedirectResponse(f"/aseguramiento?engagement_id={finding.engagement_id}#hallazgos",status_code=303)

    @app.post("/aseguramiento/{engagement_id}/emitir")
    def issue_statement(engagement_id:int,request:Request,opinion:str=Form(...),conclusion:str=Form(...),statement_date:date=Form(...),session:Session=Depends(get_db),user:dict=Depends(require_user)):
        ensure_capability(user,"external_audit");inventory=get_inventory(session,user)
        engagement=session.scalar(select(AssuranceEngagement).where(AssuranceEngagement.id==engagement_id,AssuranceEngagement.inventory_id==inventory.id).options(selectinload(AssuranceEngagement.findings)))
        if not engagement:raise HTTPException(404,"Encargo no encontrado")
        issues=assurance_readiness(engagement)
        if issues:set_flash(request,"No puede emitirse la declaración: "+" ".join(issues),"error");return RedirectResponse(f"/aseguramiento?engagement_id={engagement.id}",status_code=303)
        if not conclusion.strip():set_flash(request,"La conclusión es obligatoria.","error");return RedirectResponse(f"/aseguramiento?engagement_id={engagement.id}",status_code=303)
        engagement.opinion=opinion;engagement.conclusion=conclusion.strip();engagement.statement_date=statement_date;engagement.status="Declaración emitida"
        add_audit(session,int(user["organization_id"]),str(user["email"]),"EMITIR","Declaración de aseguramiento",f"{engagement.subject_type} {engagement.subject_reference}",new_value=f"{opinion} · {statement_date}")
        session.commit();set_flash(request,"Declaración de aseguramiento emitida. No modifica el inventario ni sustituye acreditaciones externas.");return RedirectResponse(f"/aseguramiento?engagement_id={engagement.id}",status_code=303)

    @app.get("/api/aseguramiento")
    def assurance_api(session:Session=Depends(get_db),user:dict=Depends(require_user)):
        inventory=get_inventory(session,user);items=list(session.scalars(select(AssuranceEngagement).where(AssuranceEngagement.inventory_id==inventory.id).options(selectinload(AssuranceEngagement.findings))))
        return {"inventory_id":inventory.id,"summary":assurance_summary(items),"engagements":[{"id":e.id,"subject_type":e.subject_type,"subject_reference":e.subject_reference,"status":e.status,"opinion":e.opinion,"readiness":assurance_readiness(e)} for e in items]}
