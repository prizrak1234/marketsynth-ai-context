"""Append-only BusinessVerdict tables (Commercial MVP P0.5).

Revision ID: 20260614_0033
Revises: 20260614_0032
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0033"
down_revision: Union[str, None] = "20260614_0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_verdict_evidence_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_versions", sa.JSON(), nullable=False),
        sa.Column("accepted_evidence_count", sa.Integer(), nullable=False),
        sa.Column("missing_critical_count", sa.Integer(), nullable=False),
        sa.Column("conflicting_critical_count", sa.Integer(), nullable=False),
        sa.Column("outdated_critical_count", sa.Integer(), nullable=False),
        sa.Column("area_coverage", sa.JSON(), nullable=False),
        sa.Column("readiness_status", sa.String(length=32), nullable=False),
        sa.Column("verdict_readiness_contribution", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, cols in [
        ("ix_bv_ev_snap_owner_id", ["owner_id"]),
        ("ix_bv_ev_snap_project_id", ["project_id"]),
        ("ix_bv_ev_snap_investigation_id", ["investigation_id"]),
        ("ix_bv_ev_snap_snapshot_hash", ["snapshot_hash"]),
        (
            "ix_bv_ev_snap_project_investigation_hash",
            ["project_id", "investigation_id", "snapshot_hash"],
        ),
    ]:
        op.create_index(name, "business_verdict_evidence_snapshots", cols)

    op.create_table(
        "business_verdicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_version", sa.Integer(), nullable=False),
        sa.Column("project_brief_id", sa.Uuid(), nullable=False),
        sa.Column("project_brief_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("verdict_type", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("confidence_level", sa.String(length=32), nullable=False),
        sa.Column("evidence_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("executive_conclusion", sa.String(length=2000), nullable=False),
        sa.Column("executive_rationale", sa.String(length=8000), nullable=False),
        sa.Column("primary_business_implication", sa.String(length=2000), nullable=False),
        sa.Column("recommended_next_action", sa.String(length=2000), nullable=False),
        sa.Column("supporting_evidence_summary", sa.String(length=4000), nullable=True),
        sa.Column("counter_evidence_summary", sa.String(length=4000), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("critical_risks", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("change_triggers", sa.JSON(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("readiness_snapshot", sa.String(length=32), nullable=False),
        sa.Column("prepared_by_type", sa.String(length=64), nullable=False),
        sa.Column("prepared_by_reference", sa.String(length=240), nullable=True),
        sa.Column("submitted_by", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=2000), nullable=True),
        sa.Column("supersedes_verdict_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["project_brief_id"], ["project_briefs.id"]),
        sa.ForeignKeyConstraint(
            ["evidence_snapshot_id"], ["business_verdict_evidence_snapshots.id"]
        ),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["supersedes_verdict_id"], ["business_verdicts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "version", name="uq_business_verdicts_project_version"),
    )
    for name, cols in [
        ("ix_business_verdicts_owner_id", ["owner_id"]),
        ("ix_business_verdicts_project_id", ["project_id"]),
        ("ix_business_verdicts_investigation_id", ["investigation_id"]),
        ("ix_business_verdicts_verdict_type", ["verdict_type"]),
        ("ix_business_verdicts_lifecycle_status", ["lifecycle_status"]),
        ("ix_business_verdicts_version", ["version"]),
        ("ix_business_verdicts_evidence_snapshot_hash", ["evidence_snapshot_hash"]),
        ("ix_business_verdicts_supersedes_verdict_id", ["supersedes_verdict_id"]),
        ("ix_business_verdicts_project_id_version", ["project_id", "version"]),
        ("ix_business_verdicts_project_id_lifecycle_status", ["project_id", "lifecycle_status"]),
        ("ix_business_verdicts_approved_at", ["approved_at"]),
        ("ix_business_verdicts_created_at", ["created_at"]),
    ]:
        op.create_index(name, "business_verdicts", cols)

    op.create_table(
        "business_verdict_evidence_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("verdict_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_version", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("decision_criterion", sa.String(length=240), nullable=True),
        sa.Column("materiality_at_snapshot", sa.String(length=32), nullable=False),
        sa.Column("assessment_state_at_snapshot", sa.String(length=32), nullable=False),
        sa.Column("confidence_at_snapshot", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["verdict_id"], ["business_verdicts.id"]),
        sa.ForeignKeyConstraint(["evidence_id"], ["investigation_evidence.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "verdict_id",
            "evidence_id",
            "role",
            name="uq_bv_ev_link_verdict_evidence_role",
        ),
    )
    for name, cols in [
        ("ix_bv_ev_link_owner_id", ["owner_id"]),
        ("ix_bv_ev_link_project_id", ["project_id"]),
        ("ix_bv_ev_link_verdict_id", ["verdict_id"]),
        ("ix_bv_ev_link_evidence_id", ["evidence_id"]),
        ("ix_bv_ev_link_role", ["role"]),
    ]:
        op.create_index(name, "business_verdict_evidence_links", cols)


def downgrade() -> None:
    for name in [
        "ix_bv_ev_link_role",
        "ix_bv_ev_link_evidence_id",
        "ix_bv_ev_link_verdict_id",
        "ix_bv_ev_link_project_id",
        "ix_bv_ev_link_owner_id",
    ]:
        op.drop_index(name, table_name="business_verdict_evidence_links")
    op.drop_table("business_verdict_evidence_links")

    for name in [
        "ix_business_verdicts_created_at",
        "ix_business_verdicts_approved_at",
        "ix_business_verdicts_project_id_lifecycle_status",
        "ix_business_verdicts_project_id_version",
        "ix_business_verdicts_supersedes_verdict_id",
        "ix_business_verdicts_evidence_snapshot_hash",
        "ix_business_verdicts_version",
        "ix_business_verdicts_lifecycle_status",
        "ix_business_verdicts_verdict_type",
        "ix_business_verdicts_investigation_id",
        "ix_business_verdicts_project_id",
        "ix_business_verdicts_owner_id",
    ]:
        op.drop_index(name, table_name="business_verdicts")
    op.drop_table("business_verdicts")

    for name in [
        "ix_bv_ev_snap_project_investigation_hash",
        "ix_bv_ev_snap_snapshot_hash",
        "ix_bv_ev_snap_investigation_id",
        "ix_bv_ev_snap_project_id",
        "ix_bv_ev_snap_owner_id",
    ]:
        op.drop_index(name, table_name="business_verdict_evidence_snapshots")
    op.drop_table("business_verdict_evidence_snapshots")
