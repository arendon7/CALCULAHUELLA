# Inventario arquitectónico V1.6.0

Fuente auditada: paquete local V1.5.5 Final Demo Auditada.

## Magnitud

- 118 archivos Python bajo `app/`.
- 39.011 líneas Python bajo `app/`.
- 344 rutas HTTP decoradas detectadas.
- 124 tablas ORM declaradas.

## Concentración por archivo

- `app/main.py`: 4674 líneas
- `app/database.py`: 2171 líneas
- `app/operational_imports.py`: 1110 líneas
- `app/demo_environment.py`: 1082 líneas
- `app/pilot_execution.py`: 930 líneas
- `app/reporting.py`: 918 líneas
- `app/services/product_intelligence.py`: 888 líneas
- `app/inventories_web.py`: 795 líneas
- `app/workflow_integrations.py`: 718 líneas
- `app/methodology_core.py`: 707 líneas
- `app/data_quality.py`: 649 líneas
- `app/sector_library.py`: 622 líneas

## Concentración de rutas

El principal punto de acoplamiento sigue siendo `app/main.py`, con 153 rutas detectadas. Otros módulos ya extraídos muestran que el patrón de separación funciona:

- `app/inventories_web.py`: 19 rutas
- `app/product_project_assurance_web.py`: 17 rutas
- `app/operations_web.py`: 15 rutas
- `app/information_web.py`: 11 rutas
- `app/review_web.py`: 10 rutas
- `app/pilot_execution_web.py`: 10 rutas
- `app/product_intelligence_web.py`: 9 rutas

## Distribución heurística de rutas

- metodología: 42
- inventarios: 17
- reducción: 13
- platform/admin: 13
- piloto: 13
- supply chain: 11
- data quality: 11
- review: 11
- public/onboarding: 10
- seguridad: 7
- reporting: 7
- organizations: 5
- workflow: 5
- support: 3
- calculations: 1
- otras/transversales: 175

La categoría `otras/transversales` confirma que todavía existe mucha semántica de dominio concentrada en rutas cuyos nombres no permiten inferir su bounded context. No debe usarse esta clasificación como autoridad funcional; sirve para priorizar inspección manual.

## Hotspots dentro de `app/main.py`

Entre las funciones más extensas detectadas:

- `clone_inventory_version`: 192 líneas
- `consolidation_api`: 115 líneas
- `submit_supplier_response`: 89 líneas
- `confirm_demo_payment`: 81 líneas
- `current_user`: 80 líneas
- `create_support_ticket`: 74 líneas
- `customer_success_page`: 63 líneas
- `factor_create`: 62 líneas
- `support_center`: 60 líneas
- `commercial_operations`: 56 líneas

Esto muestra dos tipos de deuda distintos:

1. rutas largas que mezclan HTTP, reglas y persistencia;
2. utilidades transversales, como `current_user`, alojadas en `main.py` aunque pertenecen a plataforma/seguridad.

## Orden de extracción recomendado

1. **Public/onboarding**: baja dependencia y alto beneficio de claridad.
2. **Reporting y reduction**: ya poseen servicios especializados, por lo que la extracción de routing tiene menor riesgo.
3. **Workflow HTML/API**: preservando `WorkItem` como orquestador y la autoridad de registros especializados.
4. **Organizations e inventories**.
5. **Data quality, methodology y calculations**: requieren gates metodológicos reforzados.
6. **Platform/admin/support**.

## Regla de refactor

Durante la primera fase:

- URLs externas permanecen estables;
- nombres de tablas permanecen estables;
- no se altera la semántica de estados;
- no se cambian factores ni fórmulas por una extracción arquitectónica;
- cada corte debe ser reversible y testeable;
- la arquitectura interna puede cambiar, los contratos del producto no.

## Primera hipótesis de corte

El primer corte debe evitar empezar por `clone_inventory_version`, pese a ser la función más larga, porque toca versionado de inventario y tiene alto riesgo funcional. Se recomienda comenzar por rutas públicas y reporting/reduction para establecer el patrón de router + servicio + tests antes de intervenir dominios más sensibles.
