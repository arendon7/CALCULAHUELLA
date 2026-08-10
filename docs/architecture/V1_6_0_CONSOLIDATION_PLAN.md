# Calcula tu Huella · V1.6.0 · Consolidación de producto

## Objetivo

Convertir la línea funcional V1.5.x en una base mantenible para evolucionar Calcula tu Huella desde demo madura hacia producto operacional, sin degradar el flujo canónico, la experiencia pública, la trazabilidad metodológica ni la cobertura de pruebas existente.

## Baseline

- `main` permanece como línea estable histórica.
- La rama funcional más avanzada en GitHub al iniciar V1.6.0 es `integration/workflow-v1.5.0`.
- La demo local V1.5.5 auditada contiene mejoras de superficie, empaquetado, CSP, documentos, instalación Mac y operación feria que todavía deben portarse de forma controlada al repositorio.
- La versión del núcleo canónico no se modifica por razones cosméticas; la versión de release/demo y la versión del núcleo deben permanecer diferenciadas.

## Principios

1. No hacer un big-bang rewrite.
2. Extraer por dominios manteniendo contratos y rutas externas estables.
3. Mantener regresión verde después de cada extracción.
4. No duplicar autoridad entre WorkItem y registros especializados.
5. Conservar aislamiento multiempresa, RBAC, CSRF, CSP y auditoría.
6. Mantener el flujo canónico de ocho etapas.
7. No fusionar a `main` mientras la línea V1.6 no tenga gates explícitos.

## Dominios objetivo

### Public y onboarding
Landing, diagnóstico, login y handoff público.

### Organizations
Organizaciones, sedes, miembros, contexto sectorial y configuración.

### Inventories
Inventarios, periodos, límites, año base, scopes y estados.

### Data collection
Solicitudes, datos de actividad, evidencias y calidad de datos.

### Methodology
Factores, fuentes, unidades, supuestos, exclusiones y criterios.

### Calculations
Conversión de actividad a emisiones, agregaciones e intensidades.

### Workflow
Mi trabajo, WorkItem, eventos, dependencias, asignación y estados.

### Review
Observaciones, hallazgos, devoluciones, aprobación y cierre.

### Reporting
Artefactos, narrativa, ejecutivo, técnico y editable.

### Reduction
Acciones, escenarios, portafolio y seguimiento.

### Security and platform
Usuarios, sesiones, roles, auditoría, health, readiness y configuración.

## Arquitectura objetivo incremental

```text
app/
  api/
    public.py
    organizations.py
    inventories.py
    data.py
    methodology.py
    calculations.py
    workflow.py
    review.py
    reports.py
    reductions.py

  domain/
    organizations/
    inventories/
    emissions/
    workflow/
    reporting/
    reduction/

  services/
  repositories/
  models/
  schemas/
  templates/
  static/
```

No se exige llegar a esta estructura en una única iteración. La arquitectura sirve como norte para extracciones reversibles.

## Fases V1.6.0

### Fase 0 · reconciliación GitHub ↔ V1.5.5

- Inventariar diferencias entre `integration/workflow-v1.5.0` y la demo local V1.5.5.
- Portar únicamente cambios validados de landing, CSP, reportes, release governance e instalador.
- Registrar explícitamente qué archivos pertenecen a producto y cuáles son solo distribución Mac.

### Fase 1 · inventario arquitectónico

- Catalogar rutas HTTP por dominio.
- Catalogar modelos/tablas por dominio.
- Identificar servicios, helpers y queries duplicados.
- Identificar funciones de `app/main.py` y `app/database.py` candidatas a extracción.
- Construir una matriz ruta → servicio → modelo → template/test.

### Fase 2 · primer corte seguro

Extraer primero dominios de bajo acoplamiento y alto valor de claridad. Prioridad propuesta:

1. rutas públicas/onboarding;
2. reporting;
3. reduction;
4. workflow API/HTML;
5. organizations/inventories;
6. data/methodology/calculations.

Cada extracción debe conservar las URLs y respuestas públicas existentes.

### Fase 3 · persistencia

- Separar creación de engine/session de modelos y seed.
- Dividir modelos por dominio sin cambiar inicialmente nombres de tablas.
- Crear repositories solo donde reduzcan duplicación real.
- Mantener Alembic como autoridad de esquema.

### Fase 4 · gates

Cada cambio debe pasar:

- tests dirigidos del dominio;
- smoke;
- multiempresa;
- roles;
- Alembic base vacía;
- templates;
- CSP/CSRF/security;
- visual QA donde cambie UI.

## Definition of Done V1.6.0

V1.6.0 se considera consolidada cuando:

- existe una rama canónica de desarrollo claramente definida;
- las mejoras validadas V1.5.5 están reconciliadas en GitHub;
- `main.py` deja de ser el punto único de registro de toda la aplicación;
- la persistencia tiene separación clara entre infraestructura, modelos y seed;
- no aumenta la duplicación de reglas de dominio;
- la regresión canónica permanece verde;
- no hay regresiones en landing, diagnóstico, Mi trabajo, cálculo, informes o reducción;
- existe backlog explícito para cualquier deuda no resuelta.

## Fuera de alcance inmediato

- Reescritura total del backend.
- Cambio de framework.
- Migración obligatoria a PostgreSQL antes de terminar la consolidación.
- Nuevos módulos comerciales grandes.
- IA generativa dentro del motor metodológico.
- Declarar producción pública lista únicamente por tener CI verde.
