from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import unicodedata


@dataclass(frozen=True)
class Scope3Category:
    code: str
    number: int
    name: str
    direction: str
    description: str
    minimum_boundary: str
    recommended_methods: tuple[str, ...]
    primary_data_priority: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["recommended_methods"] = list(self.recommended_methods)
        return payload


SCOPE3_CATEGORIES: tuple[Scope3Category, ...] = (
    Scope3Category("C1", 1, "Bienes y servicios adquiridos", "Aguas arriba", "Emisiones cradle-to-gate de bienes y servicios comprados durante el año reportado.", "Desde extracción de materias primas hasta la puerta del proveedor, sin incluir etapas ya contabilizadas en otras categorías.", ("Específico del proveedor", "Híbrido", "Promedio por actividad", "Basado en gasto"), "Alta"),
    Scope3Category("C2", 2, "Bienes de capital", "Aguas arriba", "Emisiones cradle-to-gate de activos de capital adquiridos durante el año reportado.", "Ciclo de producción del activo hasta su entrega; no amortizar emisiones salvo que el programa aplicable lo exija expresamente.", ("Específico del proveedor", "Híbrido", "Promedio por actividad", "Basado en gasto"), "Alta"),
    Scope3Category("C3", 3, "Actividades relacionadas con combustibles y energía no incluidas en alcances 1 o 2", "Aguas arriba", "Extracción, producción y transporte de combustibles y energía, incluidas pérdidas de transmisión y distribución aplicables.", "Procesos upstream y pérdidas de red no incluidos en los factores usados para alcances 1 y 2.", ("Promedio por actividad", "Específico del proveedor"), "Media"),
    Scope3Category("C4", 4, "Transporte y distribución aguas arriba", "Aguas arriba", "Transporte y distribución de compras y servicios logísticos pagados por la empresa reportante.", "Tramos, modos, carga, distancia, almacenamiento y refrigeración bajo el límite de la categoría.", ("Combustible", "Distancia", "Específico del proveedor", "Basado en gasto"), "Alta"),
    Scope3Category("C5", 5, "Residuos generados en las operaciones", "Aguas arriba", "Tratamiento y disposición por terceros de residuos generados en operaciones propias.", "Desde la entrega al gestor hasta tratamiento o disposición final, evitando duplicar transporte reportado separadamente.", ("Específico del gestor", "Tipo de residuo y tratamiento", "Promedio por actividad"), "Alta"),
    Scope3Category("C6", 6, "Viajes de negocios", "Aguas arriba", "Transporte y alojamiento de personas trabajadoras por motivos laborales en activos de terceros.", "Trayectos y noches atribuibles a viajes de negocio; excluir desplazamiento habitual casa-trabajo.", ("Distancia", "Combustible", "Basado en gasto"), "Media"),
    Scope3Category("C7", 7, "Desplazamiento de empleados", "Aguas arriba", "Traslados entre residencia y lugar de trabajo, incluido teletrabajo cuando sea material.", "Modos, distancias, ocupación, frecuencia y días laborados del periodo.", ("Encuesta de distancia", "Promedio por actividad"), "Media"),
    Scope3Category("C8", 8, "Activos arrendados aguas arriba", "Aguas arriba", "Operación de activos arrendados por la empresa que no estén incluidos en alcances 1 o 2.", "Emisiones operativas del activo durante el periodo, de acuerdo con el enfoque de consolidación organizacional.", ("Específico del activo", "Promedio por actividad"), "Media"),
    Scope3Category("C9", 9, "Transporte y distribución aguas abajo", "Aguas abajo", "Transporte, distribución y almacenamiento de productos vendidos no pagados por la empresa reportante.", "Tramos posteriores al punto de venta o control definido, con masa, distancia, modo y almacenamiento.", ("Distancia", "Específico del transportador", "Basado en gasto"), "Alta"),
    Scope3Category("C10", 10, "Procesamiento de productos vendidos", "Aguas abajo", "Procesamiento por clientes de productos intermedios vendidos.", "Procesos posteriores necesarios para convertir el producto intermedio, con escenario representativo y asignación documentada.", ("Datos del cliente", "Escenario promedio", "Promedio por actividad"), "Media"),
    Scope3Category("C11", 11, "Uso de productos vendidos", "Aguas abajo", "Emisiones directas e indirectas durante la vida útil esperada de los productos vendidos.", "Unidades vendidas, vida útil, perfiles de uso, consumo energético y emisiones directas aplicables.", ("Uso directo", "Consumo energético", "Escenario de vida útil"), "Alta"),
    Scope3Category("C12", 12, "Tratamiento al final de la vida útil de productos vendidos", "Aguas abajo", "Tratamiento y disposición de productos y empaques al terminar su vida útil.", "Masa por material, rutas de tratamiento y tasas representativas de reciclaje, valorización y disposición.", ("Tipo de material y tratamiento", "Escenario promedio"), "Media"),
    Scope3Category("C13", 13, "Activos arrendados aguas abajo", "Aguas abajo", "Operación de activos propiedad de la empresa y arrendados a terceros, no incluidos en alcances 1 o 2.", "Emisiones operativas durante el periodo atribuibles a los activos arrendados.", ("Específico del activo", "Promedio por actividad"), "Media"),
    Scope3Category("C14", 14, "Franquicias", "Aguas abajo", "Operación de franquicias no incluidas en alcances 1 o 2 de la empresa franquiciante.", "Consumos y emisiones operativas de las franquicias bajo una regla de consolidación consistente.", ("Datos de franquicia", "Promedio por actividad"), "Media"),
    Scope3Category("C15", 15, "Inversiones", "Aguas abajo", "Emisiones asociadas con inversiones, financiamiento y portafolios cuando sean aplicables.", "Clase de activo, participación o atribución financiera, límites y metodología sectorial aplicable.", ("Datos del receptor", "Atribución financiera", "Promedio sectorial"), "Alta"),
)


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return re.sub(r"\s+", " ", text)


_CATEGORY_BY_CODE = {category.code: category for category in SCOPE3_CATEGORIES}
_CATEGORY_BY_NUMBER = {category.number: category for category in SCOPE3_CATEGORIES}
_CATEGORY_ALIASES: dict[str, Scope3Category] = {}
for _category in SCOPE3_CATEGORIES:
    _CATEGORY_ALIASES[_normalize(_category.name)] = _category
    _CATEGORY_ALIASES[_normalize(f"Categoría {_category.number} · {_category.name}")] = _category
    _CATEGORY_ALIASES[_normalize(f"Categoria {_category.number} - {_category.name}")] = _category

# Common labels already used by the application and by operational teams.
for _alias, _number in {
    "Transporte aguas arriba": 4,
    "Transporte contratado": 4,
    "Transporte y distribución": 4,
    "Uso de productos vendidos": 11,
    "Bienes y servicios": 1,
    "Compras": 1,
    "Residuos": 5,
}.items():
    _CATEGORY_ALIASES[_normalize(_alias)] = _CATEGORY_BY_NUMBER[_number]


def category_from_value(value: str | int | None) -> Scope3Category | None:
    if value is None:
        return None
    if isinstance(value, int):
        return _CATEGORY_BY_NUMBER.get(value)
    raw = str(value).strip()
    if not raw:
        return None
    code_match = re.search(r"\bC\s*(1[0-5]|[1-9])\b", raw.upper())
    if code_match:
        return _CATEGORY_BY_NUMBER.get(int(code_match.group(1)))
    number_match = re.search(r"(?:categor[ií]a\s*)?(1[0-5]|[1-9])\b", raw, flags=re.IGNORECASE)
    normalized = _normalize(raw)
    if normalized in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[normalized]
    if number_match and ("categoria" in normalized or raw.strip().isdigit()):
        return _CATEGORY_BY_NUMBER.get(int(number_match.group(1)))
    for alias, category in _CATEGORY_ALIASES.items():
        if alias and (alias in normalized or normalized in alias):
            return category
    return None


def canonical_category_label(value: str | int | None) -> str:
    category = category_from_value(value)
    return f"{category.code} · {category.name}" if category else str(value or "Sin categoría")


def category_catalog() -> list[dict[str, object]]:
    return [category.to_dict() | {"label": f"{category.code} · {category.name}"} for category in SCOPE3_CATEGORIES]
