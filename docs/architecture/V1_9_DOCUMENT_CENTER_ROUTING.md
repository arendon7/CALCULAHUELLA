# V1.9 · Document Center HTTP

## Autoridad

`app/document_center_web.py` pasa a ser la autoridad HTTP de tres contratos: registro maestro, alta de documento controlado y actualización de su estado/versionado.

## Semántica preservada

Se mantienen código único por organización, versión, dueño, confidencialidad, retención, fecha de revisión, vínculo opcional a inventario/evidencia/informe y propagación de SHA-256 desde artefactos vinculados.

## Acceso e aislamiento

Las tres rutas continúan exigiendo `manage_documents`; registros, evidencias e informes se restringen a la organización activa.

## Gates

V0.13 protege creación persistente, retención e inventario vinculado. El contrato V1.9 protege autoridad HTTP, unicidad y permisos.
