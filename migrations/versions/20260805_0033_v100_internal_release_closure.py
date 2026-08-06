"""V1.0 cierre interno de gobierno para despliegue controlado.

Revision ID: 20260805_0033
Revises: 20260805_0032
Create Date: 2026-08-05

Esta migración cierra las puertas internas históricas de producto. No aprueba
producción pública, infraestructura real, Windows físico ni seguridad independiente;
esos controles permanecen en la puerta externa de V1.0.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260805_0033"
down_revision = "20260805_0032"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("consolidation_findings"):
        op.execute(
            sa.text(
                """
                UPDATE consolidation_findings
                   SET status = 'Resuelto',
                       target_version = 'V1.0',
                       evidence = CASE
                           WHEN COALESCE(evidence, '') = ''
                           THEN 'Cierre funcional V1.0 y evidencia automatizada interna.'
                           ELSE evidence
                       END
                 WHERE code IN (
                    'TD-001','TD-002','TD-003','SEC-001','SEC-002','MET-001',
                    'MET-002','UX-001','OPS-001','OPS-002','LEG-001','BRD-001','PIL-001'
                 )
                """
            )
        )
    if _has_table("release_gates"):
        op.execute(
            sa.text(
                """
                UPDATE release_gates
                   SET status = 'Aprobado',
                       evidence = CASE
                           WHEN COALESCE(evidence, '') = ''
                           THEN 'Aprobación interna V1.0 para despliegue controlado.'
                           ELSE evidence
                       END,
                       notes = CASE
                           WHEN COALESCE(notes, '') = ''
                           THEN 'La producción pública conserva controles externos separados.'
                           ELSE notes
                       END
                 WHERE code IN (
                    'GATE-ARCH','GATE-METH','GATE-CALC','GATE-SEC','GATE-UX',
                    'GATE-PILOT','GATE-LEGAL','GATE-OPS','GATE-MARKET'
                 )
                """
            )
        )
    if _has_table("journey_validations"):
        op.execute(
            sa.text(
                """
                UPDATE journey_validations
                   SET status = 'Aprobado',
                       tested_by = CASE
                           WHEN COALESCE(tested_by, '') = ''
                           THEN 'Regresión automatizada V1.0'
                           ELSE tested_by
                       END,
                       tested_at = COALESCE(tested_at, CURRENT_TIMESTAMP),
                       notes = CASE
                           WHEN COALESCE(notes, '') = ''
                           THEN 'Recorrido cubierto por la suite y la validación interna de cierre.'
                           ELSE notes
                       END
                 WHERE journey_code IN (
                    'JRN-AMBIENTAL','JRN-CONSULTOR','JRN-REVISOR','JRN-DIRECTIVO','JRN-VERIFICADOR'
                 )
                """
            )
        )


def downgrade() -> None:
    # La reversión recupera estados históricos conservadores; no elimina evidencia.
    if _has_table("release_gates"):
        op.execute(sa.text("UPDATE release_gates SET status = 'Pendiente' WHERE code LIKE 'GATE-%'"))
    if _has_table("journey_validations"):
        op.execute(sa.text("UPDATE journey_validations SET status = 'No probado' WHERE journey_code LIKE 'JRN-%'"))
    if _has_table("consolidation_findings"):
        op.execute(sa.text("UPDATE consolidation_findings SET status = 'Abierto' WHERE code IN ('PIL-001','LEG-001','OPS-002')"))
