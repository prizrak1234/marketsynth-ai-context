"""Alembic: reference_visual_assets + reference_sets (H2.6A-R).

Revision ID: 20260716_0045
Revises: 20260716_0044
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0045"
down_revision: Union[str, None] = "20260716_0044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reference_visual_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("user_request_id", sa.Uuid(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("storage_uri", sa.String(length=1000), nullable=True),
        sa.Column("content_path", sa.String(length=1000), nullable=True),
        sa.Column("asset_purpose", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
        sa.Column("quality_notes", sa.String(length=1000), nullable=True),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reference_visual_assets_owner_id", "reference_visual_assets", ["owner_id"])
    op.create_index(
        "ix_reference_visual_assets_user_request_id",
        "reference_visual_assets",
        ["user_request_id"],
    )
    op.create_index("ix_reference_visual_assets_checksum", "reference_visual_assets", ["checksum"])

    op.create_table(
        "reference_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("user_request_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("preservation_goal", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reference_asset_ids", sa.JSON(), nullable=False),
        sa.Column("primary_reference_id", sa.Uuid(), nullable=True),
        sa.Column("identity_notes", sa.Text(), nullable=True),
        sa.Column("immutable_traits", sa.JSON(), nullable=False),
        sa.Column("allowed_variations", sa.JSON(), nullable=False),
        sa.Column("forbidden_changes", sa.JSON(), nullable=False),
        sa.Column("consent_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reference_sets_owner_id", "reference_sets", ["owner_id"])
    op.create_index("ix_reference_sets_user_request_id", "reference_sets", ["user_request_id"])

    op.add_column("generated_visual_assets", sa.Column("reference_set_id", sa.Uuid(), nullable=True))
    op.add_column(
        "generated_visual_assets",
        sa.Column("used_reference_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "generated_visual_assets",
        sa.Column("excluded_reference_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "generated_visual_assets",
        sa.Column("identity_similarity", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "generated_visual_assets",
        sa.Column("brand_similarity", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "generated_visual_assets",
        sa.Column("user_accepted", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "generated_visual_assets",
        sa.Column("review_notes", sa.String(length=2000), nullable=True),
    )
    op.create_foreign_key(
        "fk_generated_visual_assets_reference_set_id",
        "generated_visual_assets",
        "reference_sets",
        ["reference_set_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_generated_visual_assets_reference_set_id",
        "generated_visual_assets",
        type_="foreignkey",
    )
    for col in (
        "review_notes",
        "user_accepted",
        "brand_similarity",
        "identity_similarity",
        "excluded_reference_ids",
        "used_reference_ids",
        "reference_set_id",
    ):
        op.drop_column("generated_visual_assets", col)
    op.drop_index("ix_reference_sets_user_request_id", table_name="reference_sets")
    op.drop_index("ix_reference_sets_owner_id", table_name="reference_sets")
    op.drop_table("reference_sets")
    op.drop_index("ix_reference_visual_assets_checksum", table_name="reference_visual_assets")
    op.drop_index(
        "ix_reference_visual_assets_user_request_id",
        table_name="reference_visual_assets",
    )
    op.drop_index("ix_reference_visual_assets_owner_id", table_name="reference_visual_assets")
    op.drop_table("reference_visual_assets")
