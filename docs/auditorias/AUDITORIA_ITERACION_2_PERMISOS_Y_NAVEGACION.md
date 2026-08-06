# Iteración 2 · Permisos, navegación y estados operativos

## Objetivo

Eliminar accesos visibles que terminaban en errores de autorización o en acciones incompatibles con el estado del proceso, sin ampliar permisos ni modificar fórmulas ambientales.

## Hallazgos corregidos

1. **Navegación sin capacidad declarada:** “Operación del servicio” aparecía para roles que no podían abrirla.
2. **Mapa de módulos indiscriminado:** `/modulos` mostraba enlaces a dominios restringidos.
3. **Recorridos y guías no sensibles al rol:** onboarding, guía, consolidación, dashboard y entrega profesional ofrecían acciones asignadas a otros perfiles.
4. **Edición de inventarios no autorizada:** Revisor, Verificador y Cliente podían ver vínculos a `/inventarios/{id}/editar` aunque el servidor los rechazaba.
5. **Controles metodológicos expuestos al Cliente:** biblioteca, pasaportes, propuestas y retiro de factores eran visibles sin capacidad metodológica.
6. **Descarga prematura de plantilla:** calidad de datos ofrecía un XLSX antes de iniciar la ejecución del piloto, terminando en 409.
7. **Accesos de organización y usuarios:** algunos recorridos ofrecían Perfil y diagnóstico o Usuarios a roles sin permiso.

## Cambios aplicados

- Se creó `can_open_route()` como política central de visibilidad por capacidades.
- Se mantuvieron intactos los controles de autorización del backend; la nueva política solo evita ofrecer acciones inviables.
- Se incorporó la política en los contextos Jinja y en ocho pantallas con rutas dinámicas.
- Se corrigió la capacidad requerida por “Operación del servicio”.
- Se convirtieron acciones ajenas al rol en información no interactiva con responsable visible.
- Se limitaron controles de factores a Consultor, Revisor o roles metodológicos autorizados.
- Se condicionó la descarga de la plantilla de calidad de datos a la existencia de una ejecución de piloto.
- Se añadieron cinco pruebas automatizadas específicas de permisos, navegación y estado.

## Validación ejecutada

### Recorrido real por rol

| Rol | Rutas HTML recorridas | Errores visibles 403/404/409/422 |
|---|---:|---:|
| Cliente | 75 | 0 |
| Consultor | 125 | 0 |
| Revisor | 118 | 0 |
| Verificador | 113 | 0 |
| Administrador | 135 | 0 |

Total: **566 comprobaciones de ruta por rol sin errores visibles**.

### Pruebas focalizadas

- Iteración 2: 5 aprobadas.
- Navegación y marca: 3 aprobadas.
- Onboarding guiado: 4 aprobadas.
- Entrega profesional: 4 aprobadas.
- Calidad de datos: 8 aprobadas.
- Biblioteca de factores: 6 aprobadas.
- Operación del servicio: 7 aprobadas.

Total focalizado: **37 pruebas aprobadas**.

### Verificaciones adicionales

- Nueve pantallas críticas renderizadas como Cliente sin enlaces restringidos.
- Código de aplicación sincronizado entre Mac y Windows.
- Compilación sintáctica integral de Python.
- No se modificaron factores de emisión, GWP, fórmulas, resultados ni datos demo.

## Resultado

La interfaz ahora respeta el principio de **“ver lo que puedo ejecutar”**. Los roles conservan acceso de consulta donde corresponde, pero dejan de encontrar botones, vínculos o formularios que terminan en errores o que pertenecen a otro responsable.

## Siguiente iteración recomendada

**Iteración 3 · Simplificación de pantallas y formularios:** reducir densidad, agrupar tareas por decisión, aplicar revelado progresivo y eliminar duplicidades operativas sin perder trazabilidad.
