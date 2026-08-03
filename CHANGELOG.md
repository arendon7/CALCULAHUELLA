# Historial de cambios

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
