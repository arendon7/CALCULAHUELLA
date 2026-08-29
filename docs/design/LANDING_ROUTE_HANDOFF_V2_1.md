# Landing route handoff · V2.1

## Decisión

La landing pública de GitHub Pages no captura ni transmite PII mientras `CALCULA_TU_HUELLA_CONFIG.appBaseUrl` esté vacío.

El diagnóstico local puede generar una ficha orientativa que contiene únicamente:

- sector;
- número de sedes;
- madurez y complejidad estimadas;
- fuentes y áreas probables;
- ruta y precio estándar de referencia;
- razones de recomendación;
- foco y siguiente paso del primer año.

La ficha puede copiarse, compartirse o imprimirse/guardarse como PDF desde el navegador.

## Handoff cuando exista aplicación pública

Con `appBaseUrl` configurado, la misma superficie habilita explícitamente:

- `GET /diagnostico` para continuar el diagnóstico oficial;
- `POST /contacto` para enviar una solicitud real;
- `GET /legal/privacidad` antes de autorizar tratamiento de datos.

El formulario de contacto exige empresa, nombre, correo, mensaje y consentimiento de privacidad. Teléfono y comunicaciones comerciales son opcionales. La landing no persiste esos campos en `localStorage`.

## Truth locks

- No se hace `POST` desde Pages en modo preview.
- La ficha orientativa no es cotización definitiva.
- No implica certificación, conformidad ISO ni verificación independiente.
- No se utiliza el CRM interno autenticado como endpoint público.
- `interest` respeta el contrato de `app/public_web.py`: Huella Esencial, Gestión de Carbono o Gestión Avanzada y Verificación.

## QA

`scripts/site_route_handoff_gate.py` valida en Chromium:

- ficha bloqueada sin diagnóstico;
- ficha coherente después del diagnóstico;
- ausencia de PII y de POST en Pages;
- copia e impresión;
- responsive móvil;
- bridge oculto sin `appBaseUrl`;
- contratos `/diagnostico`, `/contacto` y `/legal/privacidad` con app configurada;
- consentimiento de privacidad obligatorio.