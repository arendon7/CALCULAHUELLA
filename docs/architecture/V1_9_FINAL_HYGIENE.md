# V1.9 · Final composition-root hygiene

## Resultado

`_lead_complexity` se eliminó únicamente después de comprobar por AST que no existía ningún uso semántico (`Name` en contexto `Load`) en `app/` ni `tests/`. Las menciones textuales en aserciones de frontera no se confundieron con consumidores de runtime. No se trasladó ni se reimplementó lógica muerta.

## Contrato persistente

`tests/test_v190_composition_root.py` fija la frontera final: `app/main.py` puede conservar como contratos HTTP directos únicamente `/modulos`, `/api/health` y `/api/ready`. El resto de superficies HTTP deben tener autoridad modular.

## Intención arquitectónica

`main.py` queda como composition root: middleware, contexto transversal, utilidades inyectadas, registro de módulos y endpoints de salud/sistema.
