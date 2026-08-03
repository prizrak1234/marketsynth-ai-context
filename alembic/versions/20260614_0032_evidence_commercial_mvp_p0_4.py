"""Append-only Evidence tables (Commercial MVP P0.4).

Revision ID: 20260614_0032
Revises: 20260614_0031
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0032"
down_revision: Union[str, None] = "20260614_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investigation_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("claim", sa.String(length=2000), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("investigation_area", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("assessment_state", sa.String(length=32), nullable=False),
        sa.Column("confidence_level", sa.String(length=32), nullable=False),
        sa.Column("materiality", sa.String(length=32), nullable=False),
        sa.Column("review_note", sa.String(length=2000), nullable=True),
        sa.Column("why_it_matters", sa.String(length=2000), nullable=True),
        sa.Column("recommended_source_type", sa.String(length=64), nullable=True),
        sa.Column("prepared_by_type", sa.String(length=32), nullable=False),
        sa.Column("prepared_by_reference", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("supersedes_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["supersedes_evidence_id"], ["investigation_evidence.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, cols in [
        ("ix_investigation_evidence_owner_id", ["owner_id"]),
        ("ix_investigation_evidence_project_id", ["project_id"]),
        ("ix_investigation_evidence_investigation_id", ["investigation_id"]),
        ("ix_investigation_evidence_lifecycle_status", ["lifecycle_status"]),
        ("ix_investigation_evidence_assessment_state", ["assessment_state"]),
        ("ix_investigation_evidence_confidence_level", ["confidence_level"]),
        ("ix_investigation_evidence_materiality", ["materiality"]),
        ("ix_investigation_evidence_evidence_type", ["evidence_type"]),
        ("ix_investigation_evidence_investigation_area", ["investigation_area"]),
        ("ix_investigation_evidence_input_fingerprint", ["input_fingerprint"]),
        ("ix_investigation_evidence_supersedes_evidence_id", ["supersedes_evidence_id"]),
        ("ix_investigation_evidence_created_at", ["created_at"]),
    ]:
        op.create_index(name, "investigation_evidence", cols)

    op.create_table(
        "evidence_source_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("stance", sa.String(length=32), nullable=False),
        sa.Column("locator_type", sa.String(length=32), nullable=False),
        sa.Column("locator_value", sa.String(length=500), nullable=True),
        sa.Column("excerpt", sa.String(length=2000), nullable=True),
        sa.Column("excerpt_hash", sa.String(length=128), nullable=True),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["evidence_id"], ["investigation_evidence.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evidence_id",
            "source_id",
            "stance",
            name="uq_evidence_source_links_evidence_source_stance",
        ),
    )
    for name, cols in [
        ("ix_evidence_source_links_owner_id", ["owner_id"]),
        ("ix_evidence_source_links_project_id", ["project_id"]),
        ("ix_evidence_source_links_investigation_id", ["investigation_id"]),
        ("ix_evidence_source_links_evidence_id", ["evidence_id"]),
        ("ix_evidence_source_links_source_id", ["source_id"]),
        ("ix_evidence_source_links_stance", ["stance"]),
    ]:
        op.create_index(name, "evidence_source_links", cols)


def downgrade() -> None:
    for name in [
        "ix_evidence_source_links_stance",
        "ix_evidence_source_links_source_id",
        "ix_evidence_source_links_evidence_id",
        "ix_evidence_source_links_investigation_id",
        "ix_evidence_source_links_project_id",
        "ix_evidence_source_links_owner_id",
    ]:
        op.drop_index(name, table_name="evidence_source_links")
    op.drop_table("evidence_source_links")

    for name in [
        "ix_investigation_evidence_created_at",
        "ix_investigation_evidence_supersedes_evidence_id",
        "ix_investigation_evidence_input_fingerprint",
        "ix_investigation_evidence_investigation_area",
        "ix_investigation_evidence_evidence_type",
        "ix_investigation_evidence_materiality",
        "ix_investigation_evidence_confidence_level",
        "ix_investigation_evidence_assessment_state",
        "ix_investigation_evidence_lifecycle_status",
        "ix_investigation_evidence_investigation_id",
        "ix_investigation_evidence_project_id",
        "ix_investigation_evidence_owner_id",
    ]:
        op.drop_index(name, table_name="investigation_evidence")
    op.drop_table("investigation_evidence")
