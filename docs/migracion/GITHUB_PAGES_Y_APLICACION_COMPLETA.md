# GitHub Pages y aplicación completa

GitHub Pages publica archivos HTML, CSS y JavaScript estáticos. Por ello, la carpeta `site/` ofrece una vista demostrativa del producto, pero no puede ejecutar el backend Python, autenticación, base de datos, generación documental, cargas ni cálculos persistentes.

## Arquitectura de publicación prevista

- GitHub Pages: presentación pública y demo estática.
- Backend completo: contenedor de esta misma fuente canónica.
- Base de datos: PostgreSQL.
- Documentos y evidencias: almacenamiento externo versionado.
- Enlace “Abrir aplicación”: configurable en `site/config.js` cuando exista el dominio backend.

Esta separación evita simular funcionalidades que Pages no puede prestar y mantiene un único repositorio para el código completo y su vitrina pública.
