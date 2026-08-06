# Migración V1.0.0 canónica

Esta rama está preparada para recibir un único archivo llamado `canonical-upload.zip`.

Al subir el ZIP canónico certificado, GitHub Actions:

1. verifica su SHA-256;
2. descomprime el paquete;
3. elimina el contenido histórico de esta rama;
4. instala la estructura canónica completa;
5. valida manifiesto, sintaxis, versión y archivos de despliegue;
6. publica automáticamente el resultado en esta misma rama.

SHA-256 esperado:

`d4a877a7a4894be0d7f83b83f8a7e4a963112e30c57111b10b013de06c9f929c`

No fusionar esta rama con `main` hasta que la acción termine correctamente.
