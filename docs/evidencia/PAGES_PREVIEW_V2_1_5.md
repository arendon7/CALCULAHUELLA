# GitHub Pages · Living Preview V2.1.5

## Propósito

`site/` es la superficie de **preview público y UX navegable** de Calcula tu Huella. Puede sincronizarse de forma controlada a `main/site` para publicarse en GitHub Pages sin promover el backend, migraciones, cálculos o infraestructura productiva.

## Contrato

- El código funcional de FastAPI permanece gobernado por PR y gates de release.
- GitHub Pages sirve únicamente HTML/CSS/JS estático.
- La demo de plataforma en Pages usa datos demostrativos y `localStorage`; no simula persistencia de backend ni debe presentarse como aplicación productiva.
- La sincronización a `main` se limita a `site/**`.
- Los activos de marca de Pages deben conservar el canon vigente.
- Claims climáticos y de assurance deben conservar las mismas separaciones y límites que el producto real.

## V2.1.5

Incluye landing ampliada y preview navegable de:

- Mi trabajo;
- Información;
- Calidad;
- Cálculo;
- Análisis;
- Reducción;
- Control;
- Informes.

La finalidad es que las iteraciones desarrolladas en el branch activo puedan evaluarse visualmente desde el navegador antes de una promoción del backend.