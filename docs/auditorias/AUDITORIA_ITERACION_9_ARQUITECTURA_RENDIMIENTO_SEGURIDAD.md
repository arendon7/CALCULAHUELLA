# Auditoría Iteración 9 · Arquitectura, rendimiento, pruebas y seguridad

**Proyecto:** Calcula tu Huella V1.0.0  
**Fecha:** 5 de agosto de 2026  
**Alcance:** estabilización técnica sin modificar factores, GWP, fórmulas ni resultados ambientales.

## 1. Hallazgos iniciales

1. `pytest` ejecutado desde la raíz producía 45 errores de importación si no se definía `PYTHONPATH` externamente.
2. Cuarenta y tres módulos de prueba reconstruían y repoblaban repetidamente una base demostrativa de 120 modelos, elevando innecesariamente el tiempo de regresión.
3. El controlador principal seguía concentrando rutas de integraciones y API que ya constituían un dominio autónomo.
4. La aplicación no imponía un límite global previo al procesamiento de cuerpos HTTP.
5. Varias cargas leían archivos completos sin un límite de lectura explícito.
6. Tokens operativos se comparaban con igualdad ordinaria y las métricas permitían crecimiento no acotado de series por ruta.
7. Los comandos de certificación conservaban conteos y dependencias de entorno históricos.

## 2. Mejoras aplicadas

### Pruebas reproducibles y rápidas

- Se agregó `pytest.ini`; la suite funciona desde la raíz sin `PYTHONPATH`.
- Se crea una base semilla una sola vez por sesión y se restaura una copia SQLite aislada antes de cada prueba.
- Se eliminaron 43 reconstrucciones históricas de la base.
- La auditoría completa ejecuta una sola suite integral, obtiene el conteo real y registra duración y evidencia firmada.
- Se incorporó auditoría completa para macOS y Windows.

### Arquitectura

- Se extrajo `app/integrations_web.py` con seis rutas de integraciones y API.
- `app/main.py` bajó de 4.845 a 4.652 líneas.
- La arquitectura declara 15 dominios y 116 rutas con propietario explícito.
- Se actualizaron pruebas históricas frágiles para validar capacidades y mínimos estructurales, no cifras obsoletas.

### Seguridad

- Nuevo límite global `MAX_REQUEST_MB`, aplicado antes del parseo multipart, JSON o CSRF.
- Lecturas de archivos acotadas en calidad de datos, importaciones operativas y ejecución de pilotos.
- Comparación de secretos mediante `hmac.compare_digest`.
- Encabezados adicionales: COOP, CORP y bloqueo de políticas cross-domain heredadas.
- `Cache-Control: no-store` en superficies sensibles.
- Validaciones productivas para relación entre tamaño de carga y solicitud, umbral de lentitud y cardinalidad de métricas.

### Observabilidad y rendimiento

- Middleware de métricas reescrito como ASGI puro.
- Cardinalidad limitada con consolidación en `/__other__`.
- Contadores de solicitudes lentas y series colapsadas.
- Corrección del percentil p95 para muestras pequeñas.
- Variables documentadas en `.env.example`, `.env.local.example` y plantilla productiva sanitizada.

## 3. Validación ejecutada

- **macOS:** 386 pruebas aprobadas.
- **Paquete Windows evaluado en el entorno de validación:** 383 aprobadas y 3 omitidas por ser pruebas exclusivas del instalador macOS.
- **Tiempo de regresión macOS:** aproximadamente 33 segundos.
- **Tiempo de regresión del paquete Windows:** aproximadamente 33 segundos.
- **Migración desde base vacía:** aprobada en ambos paquetes hasta `20260805_0036`.
- **Persistencia:** 120 modelos ORM y 121 tablas físicas incluyendo `alembic_version`.
- **Aplicación:** 343 rutas, 80 plantillas HTML y 215 archivos Python.
- **Paridad matemática Iteración 8 vs. Iteración 9:** 200/200 cálculos, 25/25 fuentes y 4/4 inventarios idénticos.
- **Hash de resultados comparados:** `b0cb29d2bb898b47fd6e666f1c1bfd307bf41ed1ceee3bf4d4c5110c8678243d` en ambas versiones.
- **Código compartido Mac/Windows:** idéntico en `app`, `tests` y `migrations`.

## 4. Cambios deliberadamente excluidos

- No se modificaron factores de emisión, GWP, conversiones, cálculos, incertidumbre ni resultados corporativos.
- No se declara prueba física nativa en Windows 10 u 11.
- No se ejecutó pentest independiente ni prueba de carga distribuida.
- La revisión de dependencias debe realizarse dentro del entorno virtual instalado; el entorno global de construcción no constituye evidencia del paquete.
- `app/main.py` continúa siendo grande y admite una extracción adicional por dominios en una iteración posterior.

## 5. Resultado

La Iteración 9 queda **aprobada para continuar el despliegue controlado**. El paquete es reproducible, sustancialmente más rápido de validar, más estricto ante cargas y secretos, y conserva exactamente los resultados ambientales de la Iteración 8.

## 6. Próxima iteración recomendada

**Iteración 10:** certificación final Mac/Windows, recorridos multiempresa con datos piloto, pruebas de instalación física, restauración, carga concurrente y cierre de deuda arquitectónica restante.
