# V1.9 · Executive Portfolio HTTP

## Autoridad

`app/executive_portfolio_web.py` pasa a ser la autoridad HTTP de `/direccion-ejecutiva`.

## Dependencia transitoria consciente

La ruta consume `_compliance_score` por inyección porque ese helper sigue compartido con `/cumplimiento`. No se duplica ni se mueve todavía; el siguiente corte de Compliance retirará esa dependencia residual de `main.py`.

## Semántica preservada

Se mantienen emisiones del último inventario, cumplimiento, observaciones abiertas, reducción esperada, número de documentos y agregados de portafolio para todas las organizaciones accesibles.

## Gate

V0.13 protege que ambas organizaciones demo continúen presentes y que el indicador de cumplimiento promedio se renderice. El contrato V1.9 protege autoridad HTTP, unicidad y permisos.
