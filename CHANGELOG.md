# Changelog

## V1.0.0 canónica · 2026-08-05

- Unificación de Mac y Windows en una sola fuente.
- Documentación y evidencia reorganizadas.
- Flujos de CI y GitHub Pages incorporados.
- Vista previa estática para Pages.
- Preparación para reemplazo controlado de `arendon7/CALCULAHUELLA`.
- Sin cambios en el motor ambiental ni resultados certificados.

# Iteración 8 · huella de producto, mitigación y aseguramiento (2026-08-05)

- Expedientes de huella de producto con unidad declarada, límites, etapas y separación contable.
- Proyectos de mitigación con línea base, fugas, remociones, adicionalidad, titularidad y MRV.
- Encargos de validación/verificación con independencia, competencia, materialidad, hallazgos y declaración.
- Migración `20260805_0036`, tres APIs y anexos adicionales en el paquete de verificación.
- 200 componentes y 25 fuentes demostrativas idénticos a la Iteración 7.

# Iteración 7 · tierras, remociones y circularidad (2026-08-05)

- Libro mayor separado para emisiones de tierras, CO₂ biogénico, remociones, reversiones, almacenamiento en productos y beneficios circulares.
- Controles de permanencia, reversión, ciclo de vida, trazabilidad, incertidumbre y revisión.
- Ninguna remoción o emisión evitada se netea automáticamente.
- Migración 20260805_0035 y nueva API metodológica.
- Sin cambios en factores, GWP, conversiones ni resultados previamente calculados.

# Iteración 6 · Alcance 3, cadena de valor y proveedores (2026-08-05)

- Screening persistente de las 15 categorías de Alcance 3, separadas entre aguas arriba y aguas abajo.
- Clasificación por categoría: Pendiente, Material, No material o No aplica, con relevancia, justificación, responsable y estrategia de datos.
- Validación de respuestas de proveedores según método: huella total, factor por unidad o gasto.
- Pasaporte de calidad de datos con puntuación, nivel, alertas de evidencia y coherencia cuantitativa.
- Controles de unidades, límites, metodología, duplicidad y posibles solapamientos con fuentes manuales.
- Resumen por categoría, dirección, cobertura y calidad en interfaz, API y plantilla Excel.
- 200/200 componentes de cálculo y el total corporativo permanecen idénticos frente a la Iteración 5.
- Sin cambios en factores, GWP, conversiones, fórmulas o emisiones aprobadas.

# Iteración 5 · biblioteca colombiana y gobierno de factores (2026-08-05)

- Jerarquía metodológica de seis niveles para priorizar factores.
- Estado controlado de fuentes y bloqueo de documentos preliminares.
- Registro XM SIN 2025 únicamente para vigilancia, sin factor calculable.
- Alineación temporal por año del dato y año representado por la fuente.
- Filtros, pasaportes, API y exportaciones con jerarquía, vigencia y estado documental.
- 200/200 componentes de cálculo idénticos frente a la Iteración 4.
- Sin cambios en factores, GWP, conversiones, fórmulas ni resultados ambientales.

# Iteración 4 · motor metodológico (2026-08-05)

- Motor de cálculo 1.1.0 con normalización explícita de salidas g/kg/t.
- Conversiones encadenadas y control dimensional.
- GWP estricto AR4/AR5/AR6; sin fallback silencioso.
- Bloqueo de doble conteo entre CO2e agregado y gases desagregados.
- Controles de vigencia, valores finitos y gobierno de factores.
- Incertidumbre Approach 1 presentada como rango orientativo con alerta >30 %.
- 0 cambios numéricos frente a la Iteración 3 en las 25 fuentes demostrativas soportadas.

# Historial de versiones

## V1.0.0 · Iteración 3 de usabilidad y formularios

- Reduce 31 % los formularios visibles inicialmente en los cuatro recorridos críticos.
- Añade navegación interna orientada a tareas y sensible al rol.
- Aplica revelado progresivo a opciones avanzadas, propuestas, evidencias y hallazgos.
- Mantiene una sola acción abierta por grupo para evitar formularios competidores.
- Abre automáticamente secciones con errores de validación o destinos por ancla.
- Mejora el comportamiento en pantallas móviles.
- Añade pruebas específicas de estructura, recorridos y densidad operativa.
- No modifica factores, GWP, unidades, fórmulas ni resultados ambientales.

## V1.0.0 · Iteración 2 de estabilización

- Centraliza la visibilidad de rutas por capacidades sin reemplazar la autorización del backend.
- Elimina enlaces visibles que terminaban en 403, 404, 409 o 422 para los roles demo.
- Ajusta módulos, onboarding, guía, dashboard, consolidación y entrega profesional al rol activo.
- Restringe propuestas, retiros y pasaportes de factores a perfiles metodológicos autorizados.
- Habilita la plantilla de calidad únicamente cuando existe una ejecución de piloto.
- Añade pruebas de regresión específicas para navegación, permisos y estados.
- No modifica factores, GWP, fórmulas ni resultados ambientales.

## V1.0.0 · versión final para despliegue controlado

- Cierra el ciclo funcional y congela el alcance.
- Incorpora aprobación metodológica interna de Carlos Uribe.
- Incorpora aprobación jurídica interna de Agustín Rendón.
- Registra pilotos funcionales internos Greenatics y multisectorial.
- Añade términos, privacidad, DPA, SLA y alcance metodológico públicos.
- Exige consentimiento de privacidad en solicitudes comerciales.
- Separa aceptación interna, despliegue controlado y producción pública.
- Cierra hallazgos, puertas y recorridos internos mediante migración trazable.
- Mantiene bloqueadas por defecto las pruebas físicas Windows, seguridad independiente, identidad contractual e infraestructura definitiva.
- No modifica factores, GWP ni fórmulas ambientales.

## V0.57.0 · Preparación productiva

- Mapa productivo por siete capas.
- Respaldos V2 con hashes por payload y firma HMAC-SHA256.
- Réplica externa configurable y bloqueo productivo si falla.
- Inventario de objetos externos.
- Respaldo programado como automatización.
- Plantilla `.env` sanitizada.
- Stack reproducible con PostgreSQL, MinIO, Prometheus, Alertmanager, Grafana y Caddy.
- API de preparación ampliada.

## V0.56.0 · Operación del servicio

- Centro unificado para plan, capacidad, continuidad y alertas administrativas.
- Invitaciones seguras con expiración, uso único y reserva de capacidad.
- Límites efectivos para usuarios, sedes e inventarios.
- Revalidación del plan antes de aceptar una invitación.
- API administrativa y segregación de permisos.
- Migración trazable de invitaciones.
- Sin cambios en el motor ambiental.

# Historial de cambios

## V0.55.0 · informes de consultoría

- Añade un taller de informe con alistamiento y acciones por capítulo.
- Relaciona el resultado actual con un periodo anterior comparable y advierte cambios de límites, actividad o metodología.
- Calcula intensidades por producción, empleados e ingresos cuando los denominadores están disponibles.
- Genera hallazgos explicables con evidencia, implicación, prioridad y recomendación.
- Presenta limitaciones de evidencia, datos, incertidumbre, gobierno y aseguramiento.
- Incorpora guardas de comunicación para inventario cuantificado, final, verificado y carbono neutral.
- Genera un informe de consultoría editable en Word con campos de revisión profesional.
- Refuerza informes ejecutivo y técnico con gráficos, comparación, intensidades, hallazgos y recomendaciones.
- Amplía la memoria Excel con una hoja de narrativa consultiva y control editorial.
- Mantiene intactos factores, GWP, conversiones, fórmulas, modelos y migraciones.
- Conserva distribuciones independientes para macOS y Windows.

## V0.54.0 · biblioteca profesional de factores

- Centraliza las versiones de factores en un catálogo metodológico único.
- Añade filtros por actividad, sector, geografía, gas, unidad, uso, calidad y año de datos.
- Incorpora un pasaporte por versión con fuente, vigencia, tecnología, incertidumbre, memoria de conversión y restricciones.
- Evalúa cada factor contra un dato específico sin convertir el puntaje en aprobación automática.
- Compara hasta seis versiones y alerta sobre doble conteo, CO₂e agregado, GWP embebido, unidades distintas y revisiones vencidas.
- Exporta la matriz de comparación, las alertas y el contexto en Excel.
- Impide aprobar factores demostrativos, retirados, no documentados o fuera de vigencia mientras existan bloqueadores metodológicos.
- Integra la biblioteca con la conversación dato–factor y conserva el comportamiento histórico cuando no hay selección específica.
- No modifica valores de factores, conversiones, GWP, fórmulas, modelos ni migraciones.
- Mantiene distribuciones independientes para macOS y Windows.

## V0.53.0 · captura guiada y recolección sectorial

- Añade un espacio de captura priorizado por fuente, periodo, materialidad y soporte faltante.
- Permite registrar el dato de actividad y su evidencia en una sola transacción.
- Recomienda unidad, origen y soporte según la naturaleza de cada fuente.
- Presenta el periodo anterior como referencia editable y provisional, nunca como dato aprobado automático.
- Genera una plantilla Excel sectorial con plan de captura, hoja de datos, catálogos e instrucciones.
- Mantiene separado el historial completo para consulta, corrección y trazabilidad.
- Integra la captura con onboarding, centro de trabajo, calidad de datos, importaciones y cierre mensual.
- Corrige la contención móvil de formularios y tablas históricas.
- Conserva factores, GWP, conversiones, fórmulas, modelos y migraciones de V0.52.
- Mantiene distribuciones independientes para macOS y Windows.

## V0.51.0 · experiencia, coherencia y rigor ambiental

- Reorganiza el Centro de trabajo alrededor de la próxima decisión, el responsable y el criterio de cierre.
- Separa avance del proceso, confianza para decidir, nivel de publicación y requerimientos activos.
- Añade una guía contextual con seis etapas, lectura de estados, límites del producto y glosario ambiental.
- Reescribe la landing, preguntas frecuentes y mensajes operativos para explicar mejor alcance, acompañamiento y límites.
- Hace visible la organización y el sector activos para reducir errores de contexto.
- Incorpora seis preguntas ambientales antes de proponer factores y refuerza asignaciones, representatividad y doble conteo.
- Enfoca la conversación dato–factor en un registro por vez y deja el histórico bajo demanda.
- Sustituye etiquetas antiguas y evita presentar validaciones internas como certificación o verificación externa.
- Conserva factores, GWP, conversiones, fórmulas, modelos y migraciones de V0.50.
- Mantiene distribuciones independientes para macOS y Windows.

## V0.50.0 · conversaciones operativas y gobierno dato–factor

- Convierte soporte en una bandeja de mensajes, decisiones y requerimientos trazables.
- Añade referencias, tipos de solicitud, responsables, fechas, contexto y SLA por prioridad.
- Incorpora conversaciones públicas y notas internas con control de visibilidad.
- Vincula casos con inventarios, fuentes y datos de actividad.
- Añade detalle individual de caso, filtros y resumen API.
- Separa la propuesta de factor de su revisión y aprobación metodológica.
- Impide que una propuesta pendiente modifique el cálculo.
- Incorpora desglose de compatibilidad, alertas de doble conteo y evidencia de decisión.
- Conserva como válidas las selecciones heredadas de V0.49.
- Añade una migración aditiva y un modelo ORM para mensajes de soporte.
- Mantiene la distribución independiente para macOS y Windows.

## V0.49.0 · landing, paquete dual y conversación dato–factor

- Rediseña la página inicial como landing pública comercial y metodológica.
- Presenta quiénes somos, historia, diferenciadores, equipo técnico, Greenatics, precios, claridades y contacto.
- Abre la aplicación en la landing y conserva acceso separado para clientes.
- Registra solicitudes públicas dentro del embudo comercial.
- Añade instaladores independientes para Windows y conserva el ciclo seguro de macOS.
- Crea selección específica de uno o varios factores por dato de actividad.
- Evalúa compatibilidad de unidades, actividad, geografía, tecnología, temporalidad y soporte documental.
- Exige justificación, registra auditoría y recalcula al confirmar o retirar una selección.
- Mantiene como respaldo los factores generales de la fuente cuando el dato no tiene selección propia.
- Incorpora una migración aditiva y un modelo ORM nuevo.

## V0.48.0 · portafolio de reducción dirigido

- Convierte metas, acciones y escenarios en un portafolio de abatimiento gestionable.
- Cuantifica reducción requerida, reducción estructurada, cobertura y brecha frente a la meta.
- Califica la preparación de cada medida y explica los campos pendientes.
- Clasifica medidas como ganancias rápidas, apuestas estratégicas, habilitadores, en ejecución o por estructurar.
- Detecta vencimientos, compromisos próximos, concentración por responsable y embudo de ejecución.
- Proyecta la trayectoria anual de emisiones según el año de implementación.
- Añade API de resumen y libro Excel de dirección, acciones, metas, trayectoria y responsables.
- Integra cobertura y preparación del portafolio en la puerta final de entrega y en los informes.
- Mantiene intactos factores, conversiones, fórmulas, modelos de datos, migraciones y resultados históricos.

## V0.47.0 · dirección ejecutiva del inventario

- Amplía el recorrido principal a seis etapas e incorpora Reducir como etapa autónoma.
- Añade control de publicación y evita confundir cálculo disponible con resultado comunicable.
- Pondera ocho puertas de entrega y asigna responsable, criterio de aceptación y acción de cierre.
- Incorpora sala de decisión, concentración de emisiones, confianza y plan priorizado.
- Añade ficha ejecutiva de una página y refuerza informes ejecutivo, técnico y memoria Excel.
- Corrige textos residuales del recorrido y alinea navegación, dashboard y entregables.
- Mantiene intactos factores, conversiones, fórmulas, modelos, migraciones y datos históricos.
- Amplía la auditoría local a 105 pruebas focalizadas.

## V0.46.1 · consolidación y auditoría de versiones

- Compara el árbol canónico anterior, la base V0.45.5 y la entrega profesional V0.46.0.
- Confirma que V0.45.5 ya absorbía todos los archivos funcionales de V0.45.2, V0.45.3 y V0.45.4.
- Recupera la evidencia de línea base y una referencia opcional de despliegue externo, sin crear dependencia de GitHub.
- Añade auditoría local completa, inventario SHA-256 y control de archivos sensibles.
- Corrige rótulos residuales V0.45 en comandos y pantallas operativas actuales.
- Mantiene intactos factores, conversiones, fórmulas, modelos, migraciones y datos persistentes.

## V0.46.0 · entrega profesional

- Integra el recorrido completo del inventario en un centro de entrega profesional.
- Añade ocho puertas explicables de control, puntaje de alistamiento, bloqueos y siguiente acción.
- Genera una lectura ejecutiva basada en resultados, calidad, evidencia, incertidumbre, evolución y reducción.
- Distingue entre borrador técnico y versión final controlada.
- Refuerza informes PDF y memoria Excel con estado documental, limitaciones y control de entrega.
- Mantiene intactos factores, conversiones, fórmulas, modelos, migraciones y resultados históricos.

## V0.45.5 · importación y corrección guiada

- Permite elegir hoja, fila de encabezados y separador antes del mapeo.
- Añade control visual del mapeo mínimo obligatorio.
- Incorpora corrección y revalidación individual de filas sin recargar el archivo.
- Resuelve hallazgos anteriores y conserva trazabilidad de cada corrección.
- Filtra el historial por inventario activo y mejora la lectura de errores y advertencias.
- Mantiene intactos cálculos, factores, modelos y metodología.

# Registro de cambios

## V0.45.4 · primer inventario y carga inicial

- Convierte la creación del inventario en un asistente progresivo de cuatro pasos.
- Incorpora paquetes editables para servicios y oficinas, operación productiva y gestión de residuos.
- Agrega fuentes faltantes sin duplicar las ya existentes.
- Permite editar alcance, categoría, sede, responsable, frecuencia, unidad, materialidad e inclusión.
- Exige justificación al excluir una fuente del límite.
- Sugiere el primer periodo y la unidad preferida durante la carga inicial.
- Conecta creación, mapa de fuentes, datos y evidencias en un recorrido único.
- Actualiza aplicación, instaladores, documentación y pruebas a la versión 0.45.4.
- No modifica motores, factores, fórmulas, modelos, migraciones ni datos demo.

## V0.45.3 · inicio guiado y diagnóstico progresivo

- Convierte el diagnóstico público en un recorrido progresivo de cuatro pasos con validación por etapa.
- Rediseña Puesta en marcha como una ruta priorizada de seis actividades y resultados esperados.
- Integra el avance inicial y la siguiente actividad dentro del dashboard.
- Mueve Puesta en marcha a la navegación esencial para todos los roles autorizados.
- Mejora el resultado público con ruta de activación e impresión o guardado en PDF.
- Incorpora un modelo de presentación aislado para orientar el onboarding sin cambiar persistencia.
- Actualiza aplicación, instaladores, documentación y pruebas a la versión 0.45.3.
- No modifica motores, factores, fórmulas, modelos, migraciones ni datos.

## V0.45.2 · marca, navegación y experiencia consolidadas

- Fija la Marca Maestra v1 como única fuente gráfica y crea recursos canónicos verificables.
- Unifica logo, símbolo, favicon y versión invertida en todas las superficies principales.
- Reestructura portada, navegación móvil, entregables, planes y llamados a la acción.
- Mejora acceso, dashboard, responsive y accesibilidad con foco visible y estados ARIA.
- Actualiza instalador, aplicación macOS, documentación y pruebas a la versión 0.45.2.
- No modifica motores, factores, fórmulas, modelos, migraciones ni datos.

## V0.45.1 · consolidación de experiencia de usuario

- Conserva íntegramente la lógica funcional de la V0.45.
- Retira referencias internas de desarrollo de las pantallas principales orientadas al usuario.
- Alinea la oferta pública con Huella Esencial, Gestión de Carbono y Gestión Avanzada y Verificación.
- Mejora el lenguaje de portada, acceso, dashboard, diagnóstico, cálculo y onboarding.
- Presenta “Inteligencia de producto” como Perfil y alcance.
- Añade una franja responsive para empresas, consultores, entidades públicas, proyectos y productos.
- Centraliza la versión del paquete de verificación en la configuración de la aplicación.
- No modifica motores, factores, fórmulas, modelos, migraciones ni datos.
- Mantiene pendiente únicamente la sustitución del recurso gráfico anterior por el archivo maestro exacto de la Marca Maestra v1.

## V0.45 · inteligencia de producto

- Continúa directamente sobre la V0.44 completa y preserva todos sus módulos y datos.
- Incorpora perfil integral por organización: sector, modelo de negocio, procesos, sedes, energía, flota, refrigerantes, residuos, aguas, agricultura, materiales, proveedores, sistemas, gobierno y objetivos.
- Agrega diagnóstico versionado de complejidad, madurez de datos, gobierno, presión de reporte y preparación para verificación.
- Recomienda de forma explicable alcance, fuentes probables, categorías prioritarias de alcance 3, módulos, exclusiones, riesgos y siguientes pasos.
- Estructura los paquetes Huella Esencial, Gestión de Carbono y Gestión Avanzada y Verificación.
- Genera planes de implementación por fases con responsables, fechas, entregables y rutas de la plataforma.
- Mantiene la recomendación separada de la aprobación humana y registra ambas en auditoría.
- Reemplaza el diagnóstico público básico por un diagnóstico contextual con resultado explicable.
- Completa Greenatics e Industrias Andinas con perfiles, diagnósticos aprobados y planes demo idempotentes.
- Agrega el dominio `product_intelligence`, 8 rutas, 4 modelos, repositorio, servicio y API de resumen.
- Corrige la interpretación de “sin verificación externa”, que ya no eleva artificialmente el nivel recomendado.
- Incorpora migración Alembic `20260803_0029` y actualiza inventarios a versión 0.45 sin recalcular resultados históricos.

## Iteración 11 · UX, navegación y demostración multisectorial

- Vista esencial reducida a 8–9 acciones por rol.
- Vista completa con búsqueda de módulos.
- Selector rápido de empresa en la barra superior.
- Tablero con divulgación progresiva.
- Cinco empresas demo sectoriales con datos y estados distintos.
- Mac: 397 pruebas aprobadas.
- Windows: 394 aprobadas y 3 omitidas por ser exclusivas de macOS.
