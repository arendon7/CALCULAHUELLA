# Biblioteca visual de producción — Calcula tu Huella

## Propósito

Construir un sistema de imágenes, ilustraciones, diagramas y mockups reutilizable para el sitio público, la plataforma, los informes y las piezas comerciales, manteniendo una sola Marca Maestra y evitando generaciones visuales aisladas o inconsistentes.

La biblioteca no sustituye el logo oficial. El logo se incorpora siempre desde el archivo maestro exacto y como una capa independiente cuando una composición requiera marca.

## Principios

1. **Una sola identidad:** paleta, composición, iconografía y fotografía deben pertenecer al mismo sistema.
2. **Logo separado:** ninguna generación mediante IA debe redibujar o inventar el logo.
3. **Función antes que decoración:** cada imagen debe explicar, orientar, demostrar o reducir fricción.
4. **Integración real:** una imagen no se considera terminada hasta estar conectada con una plantilla y revisada en desktop y móvil.
5. **Trazabilidad:** cada activo debe tener origen, versión, dimensiones, formato, peso, hash y texto alternativo.
6. **Modularidad:** los activos deben poder reutilizarse en web, informes, presentaciones y campañas.
7. **Accesibilidad:** no se debe depender únicamente de color, texto embebido o detalles pequeños.

## Estructura propuesta

```text
app/static/img/visual/v1/
  public/
    home/
    solutions/
    organizations/
    consultants/
    territories/
    products-projects/
    methodology/
    reports/
  product/
    onboarding/
    dashboard/
    inventories/
    sources/
    data-entry/
    evidence/
    quality-review/
    calculations/
    reports/
    reduction/
    organizations/
  diagrams/
    process/
    methodology/
    data-flow/
    assurance/
  empty-states/
  backgrounds/
  social/
  manifest.json
```

## Paquetes prioritarios

### 1. Sitio público

| Código | Activo | Función |
|---|---|---|
| PUB-HOME-01 | Hero principal | Mostrar la plataforma como sistema de gestión, no como calculadora aislada |
| PUB-HOME-02 | Flujo datos → decisión | Explicar la propuesta de valor en una sola vista |
| PUB-HOME-03 | Mockup dashboard | Hacer tangible el producto |
| PUB-SOL-01 | Empresas y organizaciones | Contextualizar operación, sedes y responsables |
| PUB-SOL-02 | Consultores | Mostrar gestión multicliente y revisión profesional |
| PUB-SOL-03 | Entidades públicas | Representar territorio, instalaciones y datos públicos |
| PUB-SOL-04 | Productos y proyectos | Representar límites de producto, proyecto o evento |
| PUB-MET-01 | Arquitectura metodológica | Explicar alcance, dato, factor, gas y resultado |
| PUB-REP-01 | Informes y decisiones | Mostrar entregables ejecutivo, técnico y de reducción |

### 2. Activación y onboarding

| Código | Activo | Función |
|---|---|---|
| ONB-01 | Caracterización inicial | Explicar qué información se solicitará |
| ONB-02 | Primer inventario | Orientar la creación del periodo y alcance |
| ONB-03 | Selección de fuentes | Ayudar a reconocer fuentes relevantes |
| ONB-04 | Ruta de avance | Mostrar estado y siguiente acción |

### 3. Fuentes, datos y evidencias

| Código | Activo | Función |
|---|---|---|
| DAT-01 | Captura mensual | Aclarar dato, unidad, periodo y soporte |
| DAT-02 | Importación Excel | Explicar mapeo, validación y corrección |
| DAT-03 | Evidencia vinculada | Mostrar relación entre registro y documento |
| DAT-04 | Calidad de datos | Distinguir completo, estimado, faltante y rechazado |
| DAT-05 | Expediente documental | Hacer visible la trazabilidad del inventario |

### 4. Cálculo, revisión y aprobación

| Código | Activo | Función |
|---|---|---|
| CAL-01 | Memoria de cálculo | Dato → conversión → factor → gas → CO₂e |
| CAL-02 | Jerarquía de factores | Explicar prioridad y compatibilidad metodológica |
| REV-01 | Flujo de revisión | Preparador, revisor, aprobador y verificador |
| REV-02 | Cierre de periodo | Explicar inmutabilidad y nueva versión |
| REV-03 | Auditoría de cambios | Mostrar quién cambió qué y cuándo |

### 5. Reportes y reducción

| Código | Activo | Función |
|---|---|---|
| REP-01 | Distribución por alcance | Apoyar lectura ejecutiva |
| REP-02 | Intensidad y comparación | Explicar desempeño relativo |
| REP-03 | Informe ejecutivo | Mostrar estructura de decisión |
| RED-01 | Curva de reducción | Comparar impacto, costo y prioridad |
| RED-02 | Portafolio de iniciativas | Mostrar responsables, plazos y avance |
| RED-03 | Ruta climática | Línea base → meta → acciones → seguimiento |

## Variantes mínimas por activo

Los activos principales deben producirse en las siguientes relaciones:

- **16:9:** hero, banners, presentaciones y reportes horizontales.
- **3:2:** secciones editoriales de sitio público.
- **4:3:** tarjetas amplias, módulos y documentación.
- **1:1:** tarjetas, redes y resúmenes.
- **4:5:** navegación y campañas móviles.

Dimensiones de trabajo recomendadas:

| Relación | Maestro | Web optimizada |
|---|---:|---:|
| 16:9 | 2400 × 1350 | 1600 × 900 |
| 3:2 | 2400 × 1600 | 1500 × 1000 |
| 4:3 | 2000 × 1500 | 1200 × 900 |
| 1:1 | 1800 × 1800 | 1000 × 1000 |
| 4:5 | 1600 × 2000 | 960 × 1200 |

## Reglas para generación y composición

- Las generaciones base no deben contener logo, textos largos, cifras ni interfaces con información ilegible.
- El logo oficial se compone después con el activo exacto cuando sea necesario.
- Los mockups de interfaz deben derivarse de capturas o componentes reales de la aplicación.
- La fotografía o ilustración debe evitar clichés genéricos de hojas flotantes, manos con globos o ciudades irreales sin relación con el producto.
- Deben representarse contextos latinoamericanos y colombianos de manera profesional y no folclórica.
- Las personas no deben aparecer como decoración: deben cumplir un rol identificable dentro del proceso.
- Los elementos gráficos deben mantener paleta, contraste, iluminación y profundidad consistentes.

## Formatos de entrega

- **PNG:** transparencias, composiciones de producto y recursos que requieren fidelidad.
- **WebP:** fotografías e ilustraciones optimizadas para web.
- **SVG:** diagramas, iconos y gráficos construidos de forma vectorial; nunca para redibujar el logo sin el maestro.
- **JPG:** solo cuando no se requiera transparencia y la compresión sea visualmente segura.

## Convención de nombres

```text
<codigo>_<descripcion>_<relacion>_<variante>_v<numero>.<ext>
```

Ejemplos:

```text
PUB-HOME-01_plataforma-gestion_16x9_light_v1.webp
DAT-03_evidencia-vinculada_4x3_neutral_v1.png
RED-03_ruta-climatica_3x2_dark_v2.svg
```

No usar nombres como `imagen-final`, `imagen2`, `nueva`, `aprobada-final-final` o identificadores dependientes de una conversación.

## Metadatos obligatorios

El futuro `manifest.json` debe registrar por activo:

```json
{
  "id": "DAT-03",
  "path": "product/evidence/DAT-03_evidencia-vinculada_4x3_neutral_v1.png",
  "purpose": "Explicar la relación entre dato y soporte",
  "surface": ["source.html", "document_center.html"],
  "ratio": "4:3",
  "width": 1200,
  "height": 900,
  "bytes": 0,
  "sha256": "",
  "alt": "Registro de actividad asociado a su soporte documental",
  "origin": "generated-and-art-directed",
  "brand_overlay": false,
  "status": "planned"
}
```

Un activo no puede pasar a `approved` con campos vacíos.

## Integración en plantillas

Para cada incorporación debe verificarse:

1. propósito claro dentro de la página;
2. `alt` útil o `alt=""` cuando sea puramente decorativa;
3. ancho y alto declarados para evitar saltos de diseño;
4. `loading="lazy"` fuera del primer viewport;
5. variante móvil cuando el recorte automático destruya el significado;
6. peso razonable y formato adecuado;
7. fallback no visual para contenido esencial;
8. revisión a 1440, 1024, 768 y 390 px.

## Flujo de aprobación

```text
brief → generación/diseño → revisión de consistencia → optimización →
registro en manifest → integración en plantilla → revisión responsive → aprobación
```

Estados permitidos:

- `planned`
- `draft`
- `review`
- `approved`
- `deprecated`

## Orden de implementación

1. Recuperar e instalar Marca Maestra exacta.
2. Hero público y flujo datos → decisión.
3. Audiencias: organizaciones, consultores, entidades públicas y proyectos/productos.
4. Onboarding y primer inventario.
5. Fuentes, captura, importación y evidencias.
6. Calidad, cálculo, revisión y cierre.
7. Reportes y reducción.
8. Empty states e ilustraciones auxiliares.
9. Paquetes para informes, presentaciones y redes.

## Criterio de cierre

La biblioteca v1 se considera cerrada cuando:

- todos los activos prioritarios tienen versión aprobada;
- el manifest no contiene metadatos vacíos;
- ninguna imagen contiene un logo generado o deformado;
- sitio público y recorridos esenciales usan los activos reales;
- no hay recursos huérfanos o duplicados;
- responsive, accesibilidad y rendimiento están validados;
- los recursos pueden reutilizarse fuera de la web sin reconstruirlos.
