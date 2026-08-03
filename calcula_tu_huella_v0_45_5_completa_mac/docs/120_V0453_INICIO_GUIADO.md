# V0.45.3 · Inicio guiado y diagnóstico progresivo

## Decisión de producto

La plataforma ya contaba con diagnóstico, onboarding, dashboard y recorrido del inventario, pero cada superficie funcionaba como una pieza separada. Esta revisión las conecta en una única secuencia de adopción.

## Flujo resultante

### 1. Diagnóstico público

- Cuatro pasos: empresa, operación, datos y objetivo.
- Validación de campos obligatorios antes de avanzar.
- Progreso visible y reducción de carga cognitiva.
- Resultado explicable, no equivalente a verificación.

### 2. Puesta en marcha

- Seis actividades persistentes ya existentes.
- Priorización derivada, sin nuevas tablas ni migraciones.
- Cada actividad comunica propósito, resultado esperado, responsable, estado y acceso directo.
- Los administradores conservan la gestión de estado, responsable y fecha.

### 3. Dashboard

- Muestra el avance de implementación mientras no esté completo.
- Enlaza con la siguiente actividad prioritaria.
- Mantiene separado el avance de implementación del avance operativo del inventario.

### 4. Recorrido operativo

Una vez configurado el espacio, el inventario continúa por configurar, recolectar, calcular, revisar y reportar.

## Implementación técnica

- Nuevo helper `app/onboarding_experience.py` para construir el modelo de presentación.
- No se cambia el modelo `CustomerOnboardingItem` ni su persistencia.
- No se crean migraciones.
- El diagnóstico conserva el mismo endpoint y los mismos nombres de campos.
- La navegación esencial incorpora `Puesta en marcha`.

## Invariantes preservadas

- Factores y versiones metodológicas.
- Fórmulas y conversiones.
- Cálculos históricos.
- Modelos de dominio y migraciones.
- Datos demo y evidencias.
- Reglas de autorización existentes.
