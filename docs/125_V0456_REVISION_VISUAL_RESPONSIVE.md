# V0.45.6 — Revisión visual responsive

## Alcance

Revisión de las superficies públicas modificadas por la reconciliación de marca:

- landing pública;
- acceso/login;
- copy del shell interno;
- descriptor y claim.

La revisión se realizó sobre la fuente v0.45.5 con los cambios exactos de templates de esta rama, utilizando el entorno demostrativo local.

## Resoluciones ensayadas

| Superficie | Resolución | Ancho de contenido | Resultado |
|---|---:|---:|---|
| Landing | 1440 × 1000 | 1440 / 1440 px | Sin desbordamiento horizontal |
| Landing | 390 × 844 | 390 / 390 px | Sin desbordamiento horizontal |
| Login | 1440 × 1000 | 1440 / 1440 px | Sin desbordamiento horizontal |
| Login | 390 × 844 | 390 / 390 px | Sin desbordamiento horizontal |

## Hallazgos positivos

1. El claim “Convierte tus datos en decisiones climáticas” conserva una jerarquía clara en el hero desktop.
2. El texto introductorio explica mejor que la solución aplica a organizaciones, productos, proyectos, eventos y territorios.
3. El dashboard ilustrativo sigue siendo legible y no compite con el encabezado.
4. Las secciones de capacidades, proceso, entregables y soluciones mantienen continuidad visual.
5. La versión móvil apila correctamente hero, métricas, tarjetas, proceso, resultados y soluciones.
6. El login desktop conserva una división clara entre narrativa de marca y acceso.
7. El formulario móvil mantiene campos, botón y notas sin recortes.

## Corrección aplicada

En la versión móvil, el panel narrativo izquierdo del login se oculta por diseño. Esto hacía que el claim no fuera visible.

Se añadió:

- `app/static/css/brand-v0456.css`;
- `.login-mobile-claim` dentro de `login.html`;
- prueba automática para exigir su presencia y visualización bajo 900 px.

Resultado final móvil:

- claim visible antes del chip de acceso;
- ancho 390 / 390 px;
- altura documental aproximada: 861 px;
- formulario sin pérdida de contenido.

## Bloqueo visual confirmado

Los SVG de compatibilidad actuales contienen la identidad anterior de huella/gráfico y un descriptor heredado embebido. Esto produce:

- contradicción entre el descriptor nuevo de la interfaz y el texto incluido dentro del logo antiguo;
- baja legibilidad del logo en el header móvil;
- coexistencia visual que impide declarar cerrada la reconciliación.

Por esta razón las capturas de revisión no se incorporan como material oficial ni evidencia de Marca Maestra terminada. El cierre depende de #5.

## Pendiente después de instalar el logo exacto

Repetir las capturas y revisar:

1. proporción del logo en header desktop y móvil;
2. variante blanca en login y footer;
3. favicon en navegador;
4. separación mínima y zona de seguridad;
5. contraste sobre fondos claros y oscuros;
6. landing a 1440, 1024, 768 y 390 px;
7. login a 1440, 768 y 390 px;
8. shell interno y portal de proveedores;
9. ausencia total de referencias legacy.

## Resultado

**Copy, jerarquía y comportamiento responsive: APROBADOS.**

**Marca gráfica: PENDIENTE / BLOQUEADA por recuperación del binario maestro exacto.**
