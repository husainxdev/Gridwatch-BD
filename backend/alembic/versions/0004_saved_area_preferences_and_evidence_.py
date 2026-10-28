"""Saved area preferences and evidence index"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_schedule_coverage", "schedules", ["coverage"], postgresql_using="gin"
    )
    op.create_index(
        "ix_report_area_latest",
        "reports",
        ["location_id", "user_id", "observed_at", "created_at"],
        unique=False,
    )
    op.add_column(
        "saved_areas",
        sa.Column("label", sa.String(length=60), server_default="", nullable=False),
    )
    op.add_column(
        "saved_areas",
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index(
        "uq_default_saved_area",
        "saved_areas",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade():
    op.drop_index("ix_schedule_coverage", table_name="schedules")
    op.drop_index(
        "uq_default_saved_area",
        table_name="saved_areas",
        postgresql_where=sa.text("is_default"),
    )
    op.drop_column("saved_areas", "is_default")
    op.drop_column("saved_areas", "label")
    op.drop_index("ix_report_area_latest", table_name="reports")
