from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import select

from app.database import Base, DataImportRow, ENGINE, EmissionSource, Inventory, SessionLocal, init_db
from app.main import app
from app.operational_imports import create_operational_batch, inspect_import_file, update_operational_row


@pytest.fixture(autouse=True)
def fresh_database():
    # La base semilla aislada se restaura desde tests/conftest.py.
    yield


def login(client: TestClient) -> None:
    response = client.post('/login', data={'email': 'consultor@calculatuhuella.local', 'password': 'Demo2026!'}, follow_redirects=False)
    assert response.status_code == 303


def active_inventory(session):
    inventory = session.scalar(select(Inventory).where(Inventory.organization_id == 1, Inventory.locked.is_(False)).order_by(Inventory.id.desc()))
    source = EmissionSource(
        inventory_id=inventory.id,
        facility_id=inventory.facility_links[0].facility_id if inventory.facility_links else None,
        name='Electricidad importación guiada',
        scope=2,
        category='Electricidad adquirida',
        responsible='Pruebas',
        materiality='Alta',
        data_frequency='Mensual',
        preferred_unit='kWh',
        included=True,
    )
    session.add(source)
    session.flush()
    return inventory, source


def mapping():
    return {'source': 'Fuente', 'facility': '', 'period_start': 'Inicio', 'period_end': 'Fin', 'value': 'Valor', 'unit': 'Unidad', 'origin': 'Origen', 'estimated': '', 'evidence': 'Evidencia', 'notes': ''}


def test_v0455_health_and_customer_facing_import_page():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['version'] == '1.0.0'
        login(client)
        page = client.get('/cargas-operativas')
        assert page.status_code == 200
        assert 'Importa, valida y corrige tus datos' in page.text
        assert 'INTEGRACIÓN DE DATOS · V0.45' not in page.text


def test_v0455_xlsx_can_use_a_non_first_header_row():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['Reporte mensual'])
    sheet.append(['Generado por operaciones'])
    sheet.append(['Fuente', 'Inicio', 'Valor'])
    sheet.append(['Electricidad', date(2025, 1, 1), 120])
    output = BytesIO()
    workbook.save(output)
    result = inspect_import_file(output.getvalue(), 'reporte.xlsx', header_row=3)
    assert result['headers'] == ['Fuente', 'Inicio', 'Valor']
    assert result['rows'][0]['payload']['Valor'] == 120


def test_v0455_invalid_row_can_be_corrected_without_reuploading_file():
    with SessionLocal() as session:
        inventory, source = active_inventory(session)
        content = (
            'Fuente;Inicio;Fin;Valor;Unidad;Origen;Evidencia\n'
            f'{source.id};2025-01-01;2025-01-31;-15;kWh;Factura;\n'
        ).encode()
        batch = create_operational_batch(
            session,
            organization_id=1,
            inventory=inventory,
            filename='errores.csv',
            content=content,
            user_email='consultor@test',
            mapping=mapping(),
            defaults={'duplicate_policy': 'reject'},
        )
        session.commit()
        assert batch.error_rows == 1
        row_id = batch.rows[0].id
        update_operational_row(
            session,
            organization_id=1,
            batch_id=batch.id,
            row_id=row_id,
            user_email='consultor@test',
            source_id=source.id,
            period_start='2025-01-01',
            period_end='2025-01-31',
            value='150',
            unit='kWh',
            origin='Factura',
            evidence='Factura enero',
            notes='Corrección validada',
        )
        session.commit()
        session.refresh(batch)
        row = session.get(DataImportRow, row_id)
        assert row.status == 'Válido'
        assert row.value == 150
        assert batch.error_rows == 0
        assert batch.status == 'Validado'


def test_v0455_browser_row_correction_route_and_editor():
    with SessionLocal() as session:
        inventory, source = active_inventory(session)
        content = ('Fuente;Inicio;Fin;Valor;Unidad;Origen;Evidencia\n' f'{source.id};2025-01-01;2025-01-31;-1;kWh;Factura;\n').encode()
        batch = create_operational_batch(session, organization_id=1, inventory=inventory, filename='web.csv', content=content, user_email='consultor@test', mapping=mapping(), defaults={'duplicate_policy': 'reject'})
        session.commit()
        batch_id, row_id, source_id, inventory_id = batch.id, batch.rows[0].id, source.id, inventory.id
    with TestClient(app) as client:
        login(client)
        detail = client.get(f'/cargas-operativas?inventory_id={inventory_id}&batch_id={batch_id}')
        assert 'Guardar y revalidar fila' in detail.text
        response = client.post(
            f'/cargas-operativas/lotes/{batch_id}/filas/{row_id}/corregir',
            data={'source_id': str(source_id), 'period_start': '2025-01-01', 'period_end': '2025-01-31', 'value': '200', 'unit': 'kWh', 'origin': 'Factura', 'evidence': 'Factura enero', 'notes': ''},
            follow_redirects=False,
        )
        assert response.status_code == 303
    with SessionLocal() as session:
        row = session.get(DataImportRow, row_id)
        assert row.status == 'Válido'



def test_v0455_browser_can_reinspect_with_custom_header_row():
    with SessionLocal() as session:
        inventory, source = active_inventory(session)
        session.commit()
        inventory_id = inventory.id
    content = (
        'Reporte mensual de energía\n'
        'Fuente;Inicio;Fin;Valor;Unidad;Origen;Evidencia\n'
        f'{source.id};2025-01-01;2025-01-31;100;kWh;Factura;Factura enero\n'
    ).encode()
    with TestClient(app) as client:
        login(client)
        preview = client.post(
            '/cargas-operativas/previsualizar',
            data={'inventory_id': str(inventory_id), 'profile_id': ''},
            files={'file': ('reporte.csv', content, 'text/csv')},
            follow_redirects=False,
        )
        assert preview.status_code == 303
        location = preview.headers['location']
        token = location.split('stage=', 1)[1].split('&', 1)[0]
        page = client.get('/cargas-operativas', params={'stage': token, 'inventory_id': inventory_id, 'header_row': 2, 'delimiter': ';'})
        assert page.status_code == 200
        assert '1 filas detectadas' in page.text
        assert 'Fuente' in page.text
        assert 'Factura enero' in page.text

def test_v0455_frontend_exposes_mapping_readiness_and_read_settings():
    template = (Path(__file__).resolve().parents[1] / 'app/templates/operational_imports.html').read_text(encoding='utf-8')
    javascript = (Path(__file__).resolve().parents[1] / 'app/static/js/app.js').read_text(encoding='utf-8')
    assert 'CONFIGURACIÓN DE LECTURA' in template
    assert 'data-operational-mapping' in template
    assert 'initializeOperationalMapping' in javascript
    assert 'initializeOperationalRowEditors' in javascript
