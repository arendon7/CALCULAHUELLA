from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse

from .config import settings


def _provider_identity() -> dict[str, str]:
    return {
        "name": settings.legal_provider_name or "Proveedor por configurar",
        "nit": settings.legal_provider_nit or "Pendiente de configuración productiva",
        "address": settings.legal_notice_address or "Pendiente de configuración productiva",
        "legal_email": settings.legal_contact_email or "Pendiente de configuración productiva",
        "privacy_email": settings.privacy_contact_email or settings.legal_contact_email or "Pendiente de configuración productiva",
        "effective_date": settings.legal_effective_date,
    }


def _documents() -> dict[str, dict[str, object]]:
    provider = _provider_identity()
    name = provider["name"]
    availability = f"{settings.sla_monthly_availability_target:.1f}%"
    return {
        "terminos": {
            "title": "Términos de uso y condiciones del servicio",
            "summary": "Regulan el acceso a la plataforma, la prestación del servicio y las responsabilidades de las partes.",
            "sections": [
                ("1. Proveedor y aceptación", [
                    f"El servicio es ofrecido por {name}. La identificación tributaria, dirección y canales contractuales deberán constar en la propuesta, orden de servicio o contrato aplicable.",
                    "El acceso, la aceptación electrónica de una propuesta o el uso continuado de una cuenta implica aceptación de estos términos y de los documentos contractuales vinculados.",
                    "Los mensajes de datos, registros de aceptación, sellos de tiempo y trazas de auditoría podrán conservarse como evidencia de la relación, sin sustituir los requisitos de firma que las partes acuerden."
                ]),
                ("2. Naturaleza del servicio", [
                    "Calcula tu Huella es una plataforma de gestión de inventarios de gases de efecto invernadero y acompañamiento profesional. Organiza datos, evidencias, factores, cálculos, revisiones, informes y planes de reducción.",
                    "La plataforma no constituye por sí sola verificación independiente, certificación ISO, acreditación, declaración de neutralidad, dictamen legal ni garantía de aceptación por terceros.",
                    "El alcance técnico, nivel de revisión, entregables, sedes, periodos e integraciones se determinan en la propuesta o contrato."
                ]),
                ("3. Responsabilidades del cliente", [
                    "Suministrar información completa, lícita, comprensible y razonablemente verificable; identificar estimaciones; conservar soportes y designar responsables.",
                    "Revisar límites, metodologías, factores, supuestos, resultados e informes antes de utilizarlos en decisiones o comunicaciones externas.",
                    "Proteger credenciales, mantener actualizados los usuarios y reportar accesos o incidentes no autorizados."
                ]),
                ("4. Responsabilidades del proveedor", [
                    "Prestar el servicio con diligencia profesional, trazabilidad, control de acceso y conservación razonable de la información según el plan contratado.",
                    "Documentar las decisiones metodológicas materiales, advertir limitaciones conocidas y separar inventarios, emisiones evitadas, remociones, compensaciones y verificaciones.",
                    "Corregir defectos reproducibles y gestionar incidentes conforme al SLA aplicable."
                ]),
                ("5. Licencia, propiedad intelectual y datos", [
                    "El cliente recibe una licencia limitada, no exclusiva, no transferible y temporal para usar la plataforma durante la vigencia del servicio.",
                    "El software, la marca, las interfaces, plantillas generales y documentación base pertenecen al proveedor o a sus licenciantes. Los datos y documentos aportados por el cliente permanecen bajo su titularidad o control legítimo.",
                    "Los informes específicos y configuraciones del cliente podrán utilizarse conforme a la propuesta; el proveedor no publicará información confidencial sin autorización o deber legal."
                ]),
                ("6. Uso aceptable", [
                    "No se permite vulnerar controles, acceder a información ajena, cargar código malicioso, infringir derechos de terceros ni utilizar resultados con afirmaciones falsas o engañosas.",
                    "El proveedor podrá suspender accesos cuando exista riesgo de seguridad, incumplimiento grave, mora contractual o uso ilícito, procurando preservar la información."
                ]),
                ("7. Pagos, vigencia y terminación", [
                    "Precios, impuestos, periodicidad, renovaciones y condiciones de terminación se rigen por la propuesta o contrato.",
                    "Al finalizar, el cliente podrá solicitar exportación de su información dentro del plazo contractual. La conservación o eliminación posterior seguirá la política de privacidad, obligaciones legales y acuerdo de tratamiento."
                ]),
                ("8. Limitación y asignación de riesgos", [
                    "Los resultados dependen de la calidad de datos, evidencia, representatividad de factores y decisiones metodológicas. Ninguna estimación elimina la incertidumbre inherente.",
                    "Salvo dolo, culpa grave o límites inderogables, la responsabilidad contractual se limitará al valor pagado por el servicio durante los doce meses anteriores al hecho, sin cubrir daños indirectos, pérdida de oportunidades o decisiones tomadas sin revisión profesional.",
                    "Las limitaciones se interpretan junto con la ley aplicable y no restringen derechos irrenunciables."
                ]),
                ("9. Ley aplicable y controversias", [
                    "Se aplica la ley colombiana. Las partes procurarán negociación directa antes de acudir al mecanismo de solución de controversias previsto en el contrato.",
                    "Las condiciones particulares de una propuesta o contrato prevalecen sobre estos términos cuando exista contradicción expresa."
                ]),
            ],
        },
        "privacidad": {
            "title": "Política de tratamiento de datos personales",
            "summary": "Explica qué datos se tratan, para qué se utilizan y cómo ejercer los derechos de los titulares.",
            "sections": [
                ("1. Responsable y canales", [
                    f"Responsable: {name}. NIT: {provider['nit']}. Dirección: {provider['address']}.",
                    f"Canal de privacidad: {provider['privacy_email']}. Canal jurídico: {provider['legal_email']}.",
                    "Antes de publicación comercial deben completarse estos datos en la configuración productiva y en los contratos."
                ]),
                ("2. Datos tratados", [
                    "Datos de identificación y contacto; información laboral y organizacional; credenciales y roles; mensajes de soporte; registros de uso y seguridad; datos de facturación; y documentos aportados para inventarios ambientales.",
                    "La plataforma no requiere datos sensibles para su operación ordinaria. Si un cliente incorpora información sensible o de menores, debe contar con base legal reforzada e informar previamente al proveedor."
                ]),
                ("3. Finalidades", [
                    "Crear y administrar cuentas; responder solicitudes; prestar soporte; ejecutar contratos; facturar; proteger la plataforma; conservar trazabilidad; generar informes; atender obligaciones legales; y mejorar el servicio mediante información agregada o anonimizada.",
                    "Las comunicaciones comerciales no indispensables se enviarán únicamente cuando exista autorización o una base legal aplicable, con mecanismo para retirarla."
                ]),
                ("4. Derechos de los titulares", [
                    "Conocer, actualizar y rectificar datos; solicitar prueba de autorización; conocer el uso; presentar quejas ante la autoridad; revocar la autorización o solicitar supresión cuando proceda; y acceder gratuitamente a los datos.",
                    "Las solicitudes deben identificar al titular, describir la petición y aportar la información necesaria para verificar legitimación."
                ]),
                ("5. Encargados, transmisiones y transferencias", [
                    "Podrán utilizarse proveedores de infraestructura, correo, almacenamiento, soporte, pagos y analítica bajo contratos y controles de confidencialidad.",
                    "Cuando el cliente actúe como responsable y el proveedor procese datos por su cuenta, aplicará el Acuerdo de Tratamiento de Datos. Las transferencias internacionales se evaluarán conforme a la ley colombiana."
                ]),
                ("6. Seguridad, conservación e incidentes", [
                    "Se aplican controles de acceso, segregación por organización, cifrado en tránsito en producción, respaldos, trazabilidad y gestión de incidentes.",
                    "Los datos se conservan durante la relación y los plazos necesarios para obligaciones legales, contractuales, defensa de reclamaciones y respaldo; posteriormente se eliminan o anonimizan de forma razonable."
                ]),
                ("7. Cookies y registros técnicos", [
                    "La plataforma utiliza cookies estrictamente necesarias para sesión, seguridad y preferencias. No se activan cookies publicitarias por defecto.",
                    "Los registros técnicos pueden incluir fecha, cuenta, acción, dispositivo o dirección de red cuando sea necesario para seguridad y auditoría."
                ]),
                ("8. Vigencia y cambios", [
                    f"Vigente desde {provider['effective_date']}. Los cambios materiales se informarán por un medio razonable antes de su aplicación cuando corresponda.",
                    "Esta política se interpreta conforme a la Ley 1581 de 2012 y su reglamentación incorporada en el Decreto 1074 de 2015."
                ]),
            ],
        },
        "dpa": {
            "title": "Acuerdo de tratamiento de datos (DPA)",
            "summary": "Condiciones aplicables cuando el cliente es responsable y Calcula tu Huella actúa como encargado.",
            "sections": [
                ("1. Objeto y roles", [
                    "El cliente determina las finalidades y medios esenciales del tratamiento de datos personales incorporados a su espacio; el proveedor los trata por cuenta del cliente para prestar el servicio.",
                    "Cada parte cumplirá sus deberes como responsable o encargado y mantendrá instrucciones documentadas."
                ]),
                ("2. Instrucciones y confidencialidad", [
                    "El proveedor tratará datos únicamente para ejecutar el contrato, prestar soporte, proteger el servicio y cumplir obligaciones legales.",
                    "El personal y contratistas autorizados estarán sujetos a deberes de confidencialidad y acceso por necesidad."
                ]),
                ("3. Seguridad y subencargados", [
                    "Se aplicarán medidas razonables según naturaleza, volumen, contexto y riesgo: autenticación, autorización, registro de eventos, respaldo, recuperación, gestión de vulnerabilidades y segregación.",
                    "El proveedor podrá usar subencargados de infraestructura o servicios auxiliares, manteniendo obligaciones equivalentes y una lista disponible para el cliente."
                ]),
                ("4. Incidentes y cooperación", [
                    "El proveedor notificará al cliente sin demora indebida cuando confirme un incidente que comprometa datos bajo su encargo, incluyendo información disponible sobre naturaleza, alcance, medidas y evolución.",
                    "Se apoyarán consultas, reclamos, evaluaciones de impacto y requerimientos de autoridades en la medida razonable y conforme al contrato."
                ]),
                ("5. Retorno, eliminación y auditoría", [
                    "Al terminar el servicio, el cliente podrá exportar datos durante el periodo acordado. Después se eliminarán o devolverán, salvo conservación legal, respaldos rotativos o defensa de reclamaciones.",
                    "Las auditorías se realizarán de manera proporcional, protegiendo información de otros clientes y evitando afectación innecesaria de la operación."
                ]),
                ("6. Anexo de tratamiento", [
                    "Objeto: operación de la plataforma y acompañamiento climático. Duración: vigencia contractual y conservación posterior autorizada.",
                    "Categorías: usuarios, contactos, proveedores, responsables internos y personas identificadas en soportes. Datos: identificación, contacto, cargo, actividad, documentos y registros técnicos.",
                    "Operaciones: recolección, organización, almacenamiento, consulta, cálculo, transmisión autorizada, respaldo, exportación y eliminación."
                ]),
            ],
        },
        "sla": {
            "title": "Acuerdo de nivel de servicio (SLA)",
            "summary": "Define objetivos operativos para el servicio alojado en infraestructura productiva certificada.",
            "sections": [
                ("1. Ámbito", [
                    "Este SLA aplica únicamente a planes cloud con infraestructura productiva activada. No aplica al paquete local, ambientes demo, pruebas, integraciones del cliente ni indisponibilidad de internet del usuario.",
                    f"Objetivo de disponibilidad mensual: {availability}, sujeto a las exclusiones y créditos definidos en el contrato."
                ]),
                ("2. Severidades y respuesta inicial", [
                    "Crítica: indisponibilidad general, pérdida confirmada de datos o vulneración activa. Objetivo de respuesta: 1 hora hábil y atención continua razonable.",
                    "Alta: función principal bloqueada sin alternativa. Objetivo: 4 horas hábiles.",
                    "Media: degradación con alternativa. Objetivo: 1 día hábil. Baja: consulta o mejora. Objetivo: 2 días hábiles."
                ]),
                ("3. Continuidad y respaldo", [
                    f"Objetivo de punto de recuperación (RPO): hasta {settings.sla_rpo_hours} horas. Objetivo de recuperación (RTO): hasta {settings.sla_rto_hours} horas, salvo eventos de fuerza mayor o dependencias externas.",
                    "Los objetivos solo se consideran vigentes cuando respaldos, réplica externa y restauración han sido certificados en la infraestructura contratada."
                ]),
                ("4. Exclusiones", [
                    "Mantenimientos programados notificados; fuerza mayor; actos del cliente; credenciales comprometidas por el cliente; proveedores externos fuera del control razonable; suspensión legítima; y funciones beta identificadas.",
                    "Las métricas no incluyen fallos de dispositivos, redes o software del cliente."
                ]),
                ("5. Medición, créditos y escalamiento", [
                    "La disponibilidad se calcula sobre minutos del periodo, excluyendo eventos permitidos. Los créditos, cuando se pacten, son el remedio contractual por incumplimiento de disponibilidad, sin afectar derechos inderogables.",
                    "El cliente debe reportar el incidente por el centro de requerimientos e incluir fecha, usuarios afectados, evidencia y pasos de reproducción."
                ]),
            ],
        },
        "metodologia": {
            "title": "Alcance metodológico y limitaciones",
            "summary": "Aclara cómo se construyen los inventarios y qué afirmaciones no produce automáticamente la plataforma.",
            "sections": [
                ("1. Marcos de referencia", [
                    "La plataforma soporta inventarios organizacionales inspirados en GHG Protocol Corporate Standard, Scope 2 Guidance, Corporate Value Chain (Scope 3) Standard e ISO 14064-1:2018.",
                    "Los factores técnicos pueden provenir de fuentes oficiales, sectoriales, proveedores o IPCC 2006 con su Refinamiento 2019, siempre que se documente aplicabilidad corporativa.",
                    "Para actividades de tierra, agricultura y remociones se incorpora preparación para GHG Protocol Land Sector and Removals Standard v1.1, cuya fecha efectiva es 1 de enero de 2027."
                ]),
                ("2. Decisiones que requieren revisión", [
                    "Propósito, límites organizacionales y operacionales, periodo, fuentes materiales, calidad de datos, unidad funcional, factor, versión de GWP, supuestos, exclusiones y nivel de publicación.",
                    "Un factor no es correcto únicamente por ser oficial: debe representar actividad, tecnología, geografía, periodo y unidad del dato."
                ]),
                ("3. Gases y GWP", [
                    "Los inventarios deben utilizar una sola evaluación del IPCC por periodo y mantener consistencia con el año base, salvo revelación y recálculo justificado.",
                    "La plataforma incluye GWP100 AR6 y referencias históricas; la versión elegida debe quedar visible. Los factores agregados en CO₂e requieren identificar o revelar el GWP embebido cuando sea posible."
                ]),
                ("4. Calidad, incertidumbre y trazabilidad", [
                    "Todo resultado debe poder reconstruirse desde dato, evidencia, conversión, factor, gas, GWP y aprobación.",
                    "Los datos estimados, factores no representativos, vacíos de evidencia y exclusiones deben mostrarse como limitaciones y priorizarse en planes de mejora."
                ]),
                ("5. Separaciones obligatorias", [
                    "Inventario bruto, reducciones internas, emisiones evitadas, remociones, compensaciones y créditos se presentan por separado.",
                    "La plataforma no autoriza afirmar neutralidad, carbono negativo, verificación o conformidad con una norma sin evaluación específica y evidencia suficiente."
                ]),
                ("6. Revisión y verificación", [
                    "La aprobación interna de Carlos Uribe valida el diseño metodológico de la herramienta para uso controlado; no constituye una declaración de verificación sobre un inventario particular.",
                    "Cada inventario destinado a publicación, licitación, financiación o declaración regulatoria debe someterse al nivel de revisión o aseguramiento que corresponda a su uso."
                ]),
            ],
        },
    }


def register_legal_routes(app, templates, current_user) -> None:
    documents = _documents()

    def render(slug: str, request: Request):
        document = documents.get(slug)
        if not document:
            return None
        return templates.TemplateResponse(
            request=request,
            name="legal_document.html",
            context={
                "user": current_user(request),
                "app_settings": settings,
                "document": document,
                "provider": _provider_identity(),
                "active_slug": slug,
            },
        )

    @app.get("/legal/terminos", response_class=HTMLResponse)
    def legal_terms(request: Request):
        return render("terminos", request)

    @app.get("/legal/privacidad", response_class=HTMLResponse)
    def legal_privacy(request: Request):
        return render("privacidad", request)

    @app.get("/legal/dpa", response_class=HTMLResponse)
    def legal_dpa(request: Request):
        return render("dpa", request)

    @app.get("/legal/sla", response_class=HTMLResponse)
    def legal_sla(request: Request):
        return render("sla", request)

    @app.get("/legal/metodologia", response_class=HTMLResponse)
    def legal_methodology(request: Request):
        return render("metodologia", request)
