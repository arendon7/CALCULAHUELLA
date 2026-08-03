# Estado funcional V0.5

## Funcional

- autenticación demostrativa y roles;
- organizaciones, sedes, inventarios y fuentes;
- datos mensuales, evidencias, solicitudes e importación Excel;
- unidades, conversiones, gases y GWP;
- factores versionados y asignaciones;
- cálculos por registro, gas y CO₂e;
- observaciones con severidad y responsables;
- respuestas, correcciones, devoluciones y cierre;
- puertas de calidad calculadas;
- envío a revisión y recomendación técnica;
- aprobación independiente;
- cierre inmutable;
- reapertura como nueva versión;
- historial formal de decisiones y auditoría ampliada.

## Reglas de control implementadas

1. Un inventario cerrado no puede editar datos, evidencias, fuentes, factores asignados ni cálculos.
2. La aprobación final exige una recomendación técnica previa.
3. El revisor que recomienda no puede autoaprobar.
4. Las observaciones mayores o críticas abiertas bloquean la aprobación.
5. Fuentes incompletas, factores ausentes o errores de cálculo bloquean la aprobación.
6. Reabrir no desbloquea el histórico: crea una nueva versión vinculada.

## Parcial

- factores oficiales: la biblioteca inicial continúa siendo demostrativa;
- informes: consumen resultados reales, pero la generación documental final está pendiente;
- firma digital: se registra responsable y fecha, pero no certificado criptográfico.

## Próxima fase V0.6

- indicadores de intensidad configurables;
- comparación histórica real;
- plan de reducción persistente;
- informe ejecutivo y técnico en PDF;
- memoria de cálculo en Excel;
- versiones y descarga de entregables.
