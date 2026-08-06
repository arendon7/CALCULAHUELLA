from __future__ import annotations

from sqlalchemy import String

from app.db.models import AppUser, MethodologySourceDocument
from app.sector_library import SOURCE_DOCUMENT_SPECS
from app.security import hash_password


def _assert_specs_fit_model(model, specs: list[dict[str, object]]) -> None:
    columns = model.__table__.columns
    violations: list[str] = []
    for index, spec in enumerate(specs):
        for key, value in spec.items():
            if key not in columns or not isinstance(value, str):
                continue
            column_type = columns[key].type
            if isinstance(column_type, String) and column_type.length is not None:
                if len(value) > column_type.length:
                    violations.append(
                        f"spec[{index}].{key}: {len(value)} > {column_type.length}: {value!r}"
                    )
    assert not violations, "Valores semilla incompatibles con PostgreSQL:\n" + "\n".join(violations)


def test_methodology_source_document_specs_fit_declared_columns() -> None:
    _assert_specs_fit_model(MethodologySourceDocument, SOURCE_DOCUMENT_SPECS)


def test_password_hash_fits_declared_column() -> None:
    password_hash = hash_password("Demo2026!")
    column_type = AppUser.__table__.columns["password_hash"].type
    assert isinstance(column_type, String)
    assert column_type.length is not None
    assert len(password_hash) <= column_type.length
