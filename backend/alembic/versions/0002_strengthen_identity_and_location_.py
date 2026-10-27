"""Strengthen identity and location integrity"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "locations",
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.create_index(
        "uq_location_bn",
        "locations",
        [
            "parent_id",
            "kind",
            sa.literal_column("lower(btrim(name_bn))"),
        ],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "uq_location_en",
        "locations",
        [
            "parent_id",
            "kind",
            sa.literal_column("lower(btrim(name_en))"),
        ],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.add_column(
        "refresh_sessions", sa.Column("replaced_by_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "refresh_sessions_replaced_by_id_fkey",
        "refresh_sessions",
        "refresh_sessions",
        ["replaced_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_user_normalized_email",
        "users",
        [sa.literal_column("lower(btrim(email))")],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_user_normalized_email", table_name="users")
    op.drop_constraint(
        "refresh_sessions_replaced_by_id_fkey", "refresh_sessions", type_="foreignkey"
    )
    op.drop_column("refresh_sessions", "replaced_by_id")
    op.drop_index("uq_location_en", table_name="locations")
    op.drop_index("uq_location_bn", table_name="locations")
    op.drop_column("locations", "aliases")
