from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .database import get_db
from .delivery_readiness import professional_delivery_summary


GUIDE_STAGES = (
    {
        "number": "01",
        "name": "Diagnosticar",
        "question": "¿Qué necesita medir la organización y para qué?",
        "output": "Perfil sectorial, propósito, complejidad, datos disponibles y ruta de implementación.",
        "href": "/inteligencia-producto",
    },
    {
        "number": "02",
        "name": "Configurar",
        "question": "¿Qué límites, sedes, fuentes, responsables y criterios regirán el inventario?",
        "output": "Periodo, consolidación, alcances, materialidad, GWP, responsables y criterios documentados.",
        "href": "/metodologia/cierre",
    },
    {
        "number": "03",
        "name": "Recopilar",
        "question": "¿Qué datos y evidencias debe entregar cada responsable?",
        "output": "Solicitudes asignadas, datos de actividad, unidades, periodos y soportes relacionados.",
        "href": "/mi-trabajo",
    },
    {
        "number": "04",
        "name": "Validar y cerrar periodos",
        "question": "¿La información está completa, consistente y lista para congelarse?",
        "output": "Errores resueltos, hallazgos atendidos y periodos cerrados con trazabilidad.",
        "href": "/cierre-mensual",
    },
    {
        "number": "05",
        "name": "Calcular",
        "question": "¿Qué factor representa cada dato y cómo se reproduce el resultado?",
        "output": "Factores aprobados, conversiones, fórmulas, gases, GWP y resultados explicables.",
        "href": "/calculos",
    },
    {
        "number": "06",
        "name": "Revisar y aprobar",
        "question": "¿El resultado cumple los criterios técnicos y de control interno?",
        "output": "Observaciones resueltas, segregación de funciones, decisión y aprobación documentadas.",
        "href": "/control",
    },
    {
        "number": "07",
        "name": "Reportar y controlar publicación",
        "question": "¿Qué versión puede utilizarse, quién la aprobó y para qué destinatario?",
        "output": "Informe versionado, nivel de publicación y expediente de entrega controlado.",
        "href": "/entrega-profesional",
    },
    {
        "number": "08",
        "name": "Reducir y continuar",
        "question": "¿Qué debe cambiar y cómo se prepara el siguiente periodo?",
        "output": "Metas, medidas, responsables, seguimiento y continuidad del nuevo ciclo.",
        "href": "/reduccion",
    },
)

GLOSSARY = (
    ("Dato de actividad", "Magnitud observada que describe una actividad: kWh, litros, kilogramos, kilómetros u otra unidad verificable."),
    ("Factor de emisión", "Coeficiente que relaciona un dato de actividad con una emisión. Debe ser compatible, representativo y documentado."),
    ("Alcance 1", "Emisiones directas de fuentes que controla la organización."),
    ("Alcance 2", "Emisiones asociadas con electricidad, calor, vapor o refrigeración adquiridos."),
    ("Alcance 3", "Otras emisiones indirectas de la cadena de valor, priorizadas según relevancia y propósito."),
    ("CO₂e", "Unidad común que expresa distintos gases de efecto invernadero mediante su potencial de calentamiento global."),
    ("GWP", "Potencial de calentamiento global utilizado para convertir cada gas a CO₂ equivalente."),
    ("Evidencia", "Documento o registro que respalda origen, valor, unidad, periodo y responsable del dato."),
    ("Incertidumbre", "Rango o nivel de confianza asociado con datos, factores, supuestos y resultados."),
    ("Materialidad", "Criterio para priorizar fuentes relevantes por magnitud, riesgo, interés de usuarios o capacidad de gestión."),
    ("Emisión evitada", "Comparación contra un escenario de referencia. No debe descontarse automáticamente del inventario corporativo."),
    ("Compensación", "Instrumento separado del inventario y de la reducción interna; requiere reglas y evidencia propias."),
)


def register_experience_routes(app, templates, common_context, require_user, get_inventory) -> None:
    @app.get("/guia", response_class=HTMLResponse)
    def experience_guide(
        request: Request,
        session: Session = Depends(get_db),
        user: dict = Depends(require_user),
    ):
        inventory = get_inventory(session, user)
        delivery = professional_delivery_summary(session, inventory)
        return templates.TemplateResponse(
            request=request,
            name="guide.html",
            context=common_context(
                request,
                session,
                user,
                "guide",
                inventory=inventory,
                delivery=delivery,
                stages=GUIDE_STAGES,
                glossary=GLOSSARY,
            ),
        )
