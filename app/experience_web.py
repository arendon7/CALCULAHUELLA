from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .database import get_db
from .delivery_readiness import professional_delivery_summary


GUIDE_STAGES = (
    {
        "number": "01", "name": "Diagnóstico", "question": "¿Qué necesita medir la organización y para qué?",
        "output": "Perfil sectorial, propósito, complejidad y ruta recomendada.", "href": "/inteligencia-producto",
    },
    {
        "number": "02", "name": "Metodología", "question": "¿Qué límites, criterios y reglas regirán el inventario?",
        "output": "Periodo, enfoque de consolidación, alcances, materialidad, GWP y criterios documentados.", "href": "/metodologia/cierre",
    },
    {
        "number": "03", "name": "Fuentes y datos", "question": "¿Dónde se originan las emisiones y qué información las sustenta?",
        "output": "Fuentes, responsables, datos de actividad, unidades y evidencias vinculadas.", "href": "/inventario",
    },
    {
        "number": "04", "name": "Dato y factor", "question": "¿Qué factor representa mejor cada dato sin duplicar emisiones?",
        "output": "Factor o conjunto de factores aprobado, conversión y justificación técnica.", "href": "/calculos",
    },
    {
        "number": "05", "name": "Revisión", "question": "¿El resultado es reproducible, completo y apto para el uso previsto?",
        "output": "Calidad, incertidumbre, hallazgos, aprobación y nivel de publicación.", "href": "/entrega-profesional",
    },
    {
        "number": "06", "name": "Reducción", "question": "¿Qué debe cambiar, quién lo lidera y cómo se medirá el avance?",
        "output": "Metas, medidas, responsables, inversión, ahorro y seguimiento.", "href": "/reduccion",
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
