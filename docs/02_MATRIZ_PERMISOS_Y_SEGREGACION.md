# Matriz de permisos y segregación

La fuente canónica está en `app/access_control.py`. La interfaz `/consolidacion` muestra la matriz completa.

## Principios

- El cliente aporta datos, pero no aprueba su propio inventario.
- El consultor prepara y revisa, pero no posee aprobación final por defecto.
- El revisor puede recomendar y aprobar según el flujo configurado.
- El verificador tiene acceso de consulta y hallazgos externos, no administración.
- El administrador gobierna organización y plataforma.
- Toda consulta o modificación debe limitarse por `organization_id`.

## Pruebas obligatorias

1. Acceso permitido por capacidad.
2. Acceso denegado por rol.
3. Aislamiento entre organizaciones.
4. Protección de identificadores manipulados.
5. Separación entre preparación, revisión, aprobación y verificación.
