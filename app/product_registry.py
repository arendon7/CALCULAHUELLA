from __future__ import annotations

"""Canonical product map used by the module and consolidation views."""

PRODUCT_MODULES: list[dict[str, object]] = [
    {"layer": "Núcleo", "group": "Configuración", "name": "Perfil, diagnóstico y alcance configurable", "version": "V0.45", "status": "Funcional con aprobación humana", "route": "/inteligencia-producto", "audience": "Dirección, responsable ambiental, consultor y equipo comercial", "detail": "Perfila la operación, evalúa madurez y complejidad, recomienda alcance, paquete, módulos y plan de implementación sin sustituir la decisión metodológica humana."},
    {"layer": "Núcleo", "group": "Experiencia", "name": "Trabajo por rol y recorrido único del inventario", "version": "V0.31", "status": "Funcional", "route": "/recorrido-inventario", "audience": "Todos los roles", "detail": "Vista esencial por defecto, navegación en seis espacios de trabajo, capacidades avanzadas separadas y recorrido de cinco etapas con siguiente acción visible."},
    {"layer": "Administración interna", "group": "Plataforma", "name": "Instalación y actualización segura en macOS", "version": "V0.30", "status": "Funcional", "route": "/modulos", "audience": "Administradores y usuarios Mac", "detail": "Instalación por doble clic, datos persistentes, respaldo previo, migración automática, lanzador en Aplicaciones y limpieza controlada de versiones antiguas."},
    {"layer": "Núcleo", "group": "Resumen", "name": "Dashboard ejecutivo", "version": "V0.1", "status": "Funcional", "route": "/dashboard", "audience": "Todos", "detail": "Indicadores, alcances y principales fuentes."},
    {"layer": "Núcleo", "group": "Inventario", "name": "Empresas, sedes y configuración", "version": "V0.2", "status": "Funcional", "route": "/inventarios", "audience": "Equipo del inventario", "detail": "CRUD, límites, metodología y asistente de creación."},
    {"layer": "Núcleo", "group": "Información", "name": "Datos, solicitudes y evidencias", "version": "V0.3", "status": "Funcional", "route": "/informacion", "audience": "Equipo del inventario", "detail": "Registros mensuales, soportes, calidad e importación Excel."},
    {"layer": "Núcleo", "group": "Cálculo", "name": "Unidades, factores y motor", "version": "V0.4", "status": "Funcional", "route": "/calculos", "audience": "Consultor y revisor", "detail": "Conversiones, factores versionados, GWP y trazabilidad matemática."},
    {"layer": "Núcleo", "group": "Metodología", "name": "Fuentes, factores formales y casos patrón", "version": "V0.23", "status": "Parcial", "route": "/metodologia/nucleo", "audience": "Consultor, revisor y verificador", "detail": "Registro documental, UPME SIN 2024, GWP versionados, factores IPCC para tratamiento biológico y validación reproducible."},
    {"layer": "Núcleo", "group": "Piloto", "name": "Preparación del inventario real de Greenatics", "version": "V0.23", "status": "En preparación", "route": "/piloto-greenatics", "audience": "Equipo ambiental, operaciones y consultor", "detail": "Matriz por sede, responsables, evidencias, cobertura de factores y plantilla de captura para Yarumal y Támesis."},
    {"layer": "Núcleo", "group": "Control", "name": "Revisión, aprobación y auditoría", "version": "V0.5", "status": "Funcional", "route": "/control", "audience": "Consultor, revisor y aprobador", "detail": "Observaciones, segregación, cierre inmutable y reapertura versionada."},
    {"layer": "Núcleo", "group": "Gestión", "name": "Análisis, indicadores y reducción", "version": "V0.6", "status": "Funcional", "route": "/analisis", "audience": "Equipo ambiental y dirección", "detail": "Intensidades, comparación histórica, metas y acciones de reducción."},
    {"layer": "Núcleo", "group": "Entregables", "name": "Informes y memoria", "version": "V0.6", "status": "Funcional", "route": "/reportes", "audience": "Todos", "detail": "Informe ejecutivo, informe técnico y memoria de cálculo Excel."},
    {"layer": "Avanzado", "group": "Configuración", "name": "Modelos sectoriales y metas", "version": "V0.7", "status": "Funcional", "route": "/sectorizacion", "audience": "Consultor", "detail": "Plantillas sectoriales, fuentes sugeridas y metas corporativas."},
    {"layer": "Avanzado", "group": "Descarbonización", "name": "Escenarios y curva de abatimiento", "version": "V0.8", "status": "Funcional", "route": "/escenarios", "audience": "Consultor y dirección", "detail": "Portafolios, adopción, costo marginal y trayectoria proyectada."},
    {"layer": "Avanzado", "group": "Aseguramiento", "name": "Portal del verificador", "version": "V0.8", "status": "Funcional", "route": "/verificacion", "audience": "Verificador", "detail": "Hallazgos externos, respuestas y paquete ZIP reproducible."},
    {"layer": "Avanzado", "group": "Cadena de valor", "name": "Proveedores y alcance 3", "version": "V0.9", "status": "Funcional", "route": "/cadena-valor", "audience": "Compras, proveedor y consultor", "detail": "Campañas, enlaces seguros, factores específicos y consolidación."},
    {"layer": "Avanzado", "group": "Gobierno", "name": "Cumplimiento, metodología y documentos", "version": "V0.13", "status": "Funcional", "route": "/cumplimiento", "audience": "Consultor, revisor y verificador", "detail": "Matriz de cumplimiento, releases metodológicos y control documental."},
    {"layer": "Avanzado", "group": "Inteligencia de impacto", "name": "Benchmarking e intensidades", "version": "V0.18", "status": "Funcional", "route": "/inteligencia-impacto", "audience": "Dirección", "detail": "Snapshots, referencias documentadas y valor financiero del abatimiento."},
    {"layer": "Avanzado", "group": "Riesgo climático", "name": "Riesgos, controles y transición", "version": "V0.19", "status": "Funcional", "route": "/riesgos-climaticos", "audience": "Dirección y gestión de riesgos", "detail": "Matriz inherente/residual, controles, exposición y hoja de ruta."},
    {"layer": "Avanzado", "group": "Divulgación climática", "name": "Escenarios e informe para comité", "version": "V0.20", "status": "Funcional", "route": "/divulgacion-climatica", "audience": "Comité directivo", "detail": "Sensibilidad financiera, matriz de divulgación y paquete ejecutivo."},
    {"layer": "Administración interna", "group": "Operación", "name": "Seguridad, continuidad y respaldos", "version": "V0.34", "status": "Restauración ensayada", "route": "/operacion", "audience": "Administrador", "detail": "CSRF, cadena hash, logs estructurados, respaldos verificables y ensayos de restauración aislados con evidencia auditable."},
    {"layer": "Núcleo", "group": "Piloto", "name": "Centro de control del piloto Greenatics", "version": "V0.33", "status": "Piloto controlado", "route": "/piloto-greenatics/ejecucion", "audience": "Consultor, responsables de datos, revisor y aprobador", "detail": "Controla Yarumal, Támesis y operación corporativa por fuente, mes, evidencia, factor, incidencia y contraste independiente."},
    {"layer": "Núcleo", "group": "Información", "name": "Calidad y aplicación de datos reales", "version": "V0.26", "status": "Beta operativa", "route": "/calidad-datos", "audience": "Responsables de datos, consultor y revisor", "detail": "Valida archivos antes de aplicarlos: códigos, periodos, unidades, duplicados, evidencia, estimaciones, atípicos y trazabilidad por lote."},
    {"layer": "Núcleo", "group": "Control mensual", "name": "Conciliación y cierre de periodos", "version": "V0.27", "status": "Beta operativa", "route": "/cierre-mensual", "audience": "Responsables de datos, consultor, revisor y aprobador", "detail": "Conciliación por fuente, puertas de datos y metodología, revisión, cierre con hash y reapertura auditada."},
    {"layer": "Administración interna", "group": "Plataforma", "name": "Migraciones, almacenamiento y notificaciones", "version": "V0.11", "status": "Funcional", "route": "/administracion-plataforma", "audience": "Administrador", "detail": "Alembic, almacenamiento S3, correo y administración avanzada."},
    {"layer": "Administración interna", "group": "Operación empresarial", "name": "Automatizaciones, integraciones y multiempresa", "version": "V0.12", "status": "Funcional", "route": "/automatizaciones", "audience": "Administrador y consultor", "detail": "Recordatorios, API de entrada, integraciones y cambio de organización."},
    {"layer": "Administración interna", "group": "Servicio SaaS", "name": "Onboarding, planes, uso y soporte", "version": "V0.14", "status": "Funcional", "route": "/cuenta-servicio", "audience": "Administrador SaaS", "detail": "Implementación, suscripciones, límites, soporte y administración."},
    {"layer": "Administración interna", "group": "Comercial", "name": "Prospectos, propuestas y pagos demostrativos", "version": "V0.15", "status": "Funcional", "route": "/comercial", "audience": "Equipo comercial", "detail": "Diagnóstico, CRM, propuestas, aceptación y webhook firmado."},
    {"layer": "Administración interna", "group": "Operación comercial", "name": "Contratos, cartera y renovaciones", "version": "V0.16", "status": "Funcional", "route": "/operacion-comercial", "audience": "Equipo comercial y financiero", "detail": "Contratos versionados, órdenes, cobros, cartera y renovaciones."},
    {"layer": "Administración interna", "group": "Éxito del cliente", "name": "Adopción, salud y valor", "version": "V0.17", "status": "Funcional", "route": "/exito-cliente", "audience": "Customer success", "detail": "Plan de éxito, salud explicable, hitos y pronóstico de renovación."},
    {"layer": "Administración interna", "group": "Consolidación", "name": "Auditoría y preparación de V1.0", "version": "V0.21", "status": "Funcional", "route": "/consolidacion", "audience": "Producto, metodología y administración", "detail": "Capas de producto, deuda técnica, puertas de salida, permisos y recorridos por rol."},
    {"layer": "Administración interna", "group": "Consolidación", "name": "Arquitectura por dominios y preparación de V1.0", "version": "V0.45", "status": "Certificación operativa", "route": "/operacion#despliegue-controlado", "audience": "Producto, tecnología y administración", "detail": "Respaldo, restauración, puerta productiva, servicios externos y paquete de certificación firmado."},
    {"layer": "Núcleo", "group": "Metodología", "name": "Biblioteca Colombia y calculadoras sectoriales", "version": "V0.28", "status": "Piloto controlado", "route": "/metodologia/colombia", "audience": "Consultor, revisor y verificador", "detail": "Factores y métodos documentados para combustibles, aguas residuales, N aplicado al suelo y balance operativo de biogás, con restricciones explícitas."},
    {"layer": "Núcleo", "group": "Información", "name": "Cargas operativas configurables", "version": "V0.29", "status": "Funcional", "route": "/cargas-operativas", "audience": "Responsables de datos, consultor y revisor", "detail": "Importación CSV/XLSX con mapeo reutilizable, previsualización, control de duplicados, validación por fila, aplicación auditada y trazabilidad de origen."},
]

ROLE_JOURNEYS: list[dict[str, object]] = [
    {
        "code": "JRN-AMBIENTAL", "name": "Responsable ambiental", "role": "Cliente",
        "objective": "Completar información y llevar el inventario hasta cálculo.",
        "steps": [
            ("Consultar inventario", "/inventarios"), ("Revisar solicitudes", "/informacion"),
            ("Cargar archivo operativo", "/cargas-operativas"), ("Gestionar datos y evidencias", "/informacion"), ("Consultar avance", "/dashboard"),
            ("Conciliar el periodo", "/cierre-mensual"), ("Responder observaciones", "/control"),
        ],
    },
    {
        "code": "JRN-CONSULTOR", "name": "Consultor metodológico", "role": "Consultor",
        "objective": "Configurar, calcular, revisar y preparar los entregables.",
        "steps": [
            ("Configurar límites", "/inventarios"), ("Definir fuentes", "/inventario"),
            ("Asignar factores", "/metodologia"), ("Recalcular", "/calculos"),
            ("Enviar cierre mensual", "/cierre-mensual"), ("Gestionar observaciones", "/control"), ("Generar informes", "/reportes"),
        ],
    },
    {
        "code": "JRN-REVISOR", "name": "Revisor independiente", "role": "Revisor",
        "objective": "Evaluar calidad, formular hallazgos y recomendar aprobación.",
        "steps": [
            ("Revisar metodología", "/metodologia"), ("Evaluar evidencias", "/informacion"),
            ("Revisar cálculos", "/calculos"), ("Cerrar el periodo", "/cierre-mensual"),
            ("Levantar observaciones", "/control"), ("Recomendar aprobación", "/control"),
        ],
    },
    {
        "code": "JRN-DIRECTIVO", "name": "Directivo", "role": "Administrador",
        "objective": "Comprender resultados y adoptar decisiones climáticas.",
        "steps": [
            ("Consultar dashboard", "/dashboard"), ("Revisar impacto", "/inteligencia-impacto"),
            ("Evaluar reducción", "/reduccion"), ("Revisar riesgos", "/riesgos-climaticos"),
            ("Tomar decisiones", "/divulgacion-climatica"),
        ],
    },
    {
        "code": "JRN-VERIFICADOR", "name": "Verificador externo", "role": "Verificador",
        "objective": "Reproducir la evidencia y documentar una revisión externa.",
        "steps": [
            ("Consultar inventario", "/inventarios"), ("Revisar metodología", "/metodologia"),
            ("Examinar paquete", "/verificacion"), ("Registrar hallazgos", "/verificacion"),
            ("Verificar respuesta", "/verificacion"),
        ],
    },
]


def product_layers() -> list[dict[str, object]]:
    order = ["Núcleo", "Avanzado", "Administración interna"]
    return [
        {
            "name": layer,
            "modules": [module for module in PRODUCT_MODULES if module["layer"] == layer],
        }
        for layer in order
    ]
