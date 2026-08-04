# Política de ingreso de versiones canónicas

## Propósito

Evitar que GitHub cambie repetidamente de base por versiones todavía en desarrollo. Una conversación puede seguir iterando V0.50, V0.51 o posteriores, pero el repositorio solo adopta una versión cuando existe una entrega verificable y autocontenida.

## Estados

### En desarrollo

Existe código o una iteración activa, pero falta uno o varios de estos elementos:

- ZIP final;
- SHA-256;
- manifiesto;
- validación;
- inventario de archivos;
- migración desde base vacía;
- pruebas focalizadas;
- activos visuales completos.

Una versión en desarrollo no reemplaza la rama canónica ni abre una nueva migración principal.

### Candidata

Existe ZIP, checksum, manifiesto y validación, pero aún no se ha importado ni ejecutado en GitHub.

La versión se trabaja en una rama `migration/vX.Y.Z-canonical` y su PR permanece como borrador.

### Canónica en GitHub

La fuente fue importada, el ZIP fue eliminado después de descomprimirlo, CI pasó y la vista previa fue revisada.

### Fusionada

La versión canónica fue reconciliada con mejoras pendientes y fusionada a `develop`.

## Puertas obligatorias

Una versión solo puede pasar a candidata cuando se dispone de:

1. nombre exacto del archivo;
2. SHA-256 del archivo;
3. manifiesto de contenido;
4. documento de validación;
5. versión runtime coherente;
6. revisión Alembic declarada;
7. conteo de rutas, modelos y plantillas;
8. pruebas funcionales y de seguridad;
9. inventario sin bases, secretos, evidencias, logs ni cachés;
10. logos, favicons e imágenes requeridos.

Una versión solo puede pasar a canónica en GitHub cuando:

1. el hash del ZIP coincide;
2. la extracción es segura;
3. el árbol importado compila;
4. Alembic migra desde base vacía;
5. las pruebas focalizadas pasan;
6. Docker construye;
7. Codespaces inicia y responde;
8. la landing, login y flujos críticos se revisan;
9. el PR es fusionable;
10. el ZIP ya no permanece en el repositorio.

## Versión vigente

- **V0.49.0:** última entrega completa y validada; candidata canónica en PR #12.
- **V0.50:** observada en desarrollo en otra conversación; no existe evidencia de ZIP final validado y no reemplaza V0.49.0 todavía.

## Reconciliación de mejoras paralelas

Los cambios del PR #4 no se descartan. Después de importar la versión canónica se comparan por archivo y capacidad. Solo se portan los cambios que:

- no estén ya presentes;
- no retrocedan la versión;
- no sustituyan logos oficiales;
- no cambien metodología sin decisión explícita;
- conserven pruebas y trazabilidad.
