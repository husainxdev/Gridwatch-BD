"""Private activities, concurrency versions and history index."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = depends_on = None


def upgrade():
    for table in ("locations", "reports", "outage_events"):
        op.add_column(
            table,
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )
    op.create_table(
        "activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("ends_at > starts_at", name="activity_interval"),
    )
    op.create_index("ix_activity_owner_start", "activities", ["user_id", "starts_at"])
    op.create_index(
        "ix_episode_owner_area_time",
        "personal_episodes",
        ["user_id", "location_id", "last_observed_at"],
    )


def downgrade():
    op.drop_index("ix_episode_owner_area_time", table_name="personal_episodes")
    op.drop_table("activities")
    for table in ("locations", "reports", "outage_events"):
        op.drop_column(table, "version")
