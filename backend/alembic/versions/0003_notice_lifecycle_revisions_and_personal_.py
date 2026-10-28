"""Notice lifecycle revisions and personal observations"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "evidence_audit",
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_audit_entity_id"),
        "evidence_audit",
        ["entity_id"],
        unique=False,
    )
    op.create_table(
        "personal_episodes",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_personal_episodes_user_id"),
        "personal_episodes",
        ["user_id"],
        unique=False,
    )
    op.add_column(
        "notices",
        sa.Column(
            "lifecycle", sa.String(length=20), server_default="draft", nullable=False
        ),
    )
    op.add_column(
        "notices",
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "notices",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("notices", sa.Column("created_by", sa.UUID(), nullable=True))
    op.add_column("notices", sa.Column("updated_by", sa.UUID(), nullable=True))
    op.alter_column(
        "notices",
        "published_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.create_foreign_key(None, "notices", "users", ["created_by"], ["id"])
    op.create_foreign_key(None, "notices", "users", ["updated_by"], ["id"])
    op.add_column(
        "reports",
        sa.Column("note", sa.String(length=500), server_default="", nullable=False),
    )
    op.add_column(
        "reports",
        sa.Column(
            "moderation",
            sa.String(length=20),
            server_default="accepted",
            nullable=False,
        ),
    )
    op.add_column(
        "reports",
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("reports", sa.Column("episode_id", sa.UUID(), nullable=True))
    op.add_column("reports", sa.Column("candidate_event_id", sa.UUID(), nullable=True))
    op.create_foreign_key(None, "reports", "personal_episodes", ["episode_id"], ["id"])
    op.create_foreign_key(
        None, "reports", "outage_events", ["candidate_event_id"], ["id"]
    )
    op.add_column(
        "schedules",
        sa.Column(
            "lifecycle", sa.String(length=20), server_default="draft", nullable=False
        ),
    )
    op.add_column(
        "schedules",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "schedules",
        sa.Column(
            "category",
            sa.String(length=100),
            server_default="maintenance",
            nullable=False,
        ),
    )
    op.add_column(
        "schedules",
        sa.Column(
            "coverage",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.add_column(
        "schedules",
        sa.Column(
            "coverage_scope",
            sa.String(length=30),
            server_default="named_locations",
            nullable=False,
        ),
    )
    op.add_column(
        "schedules",
        sa.Column("is_demo", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("schedules", sa.Column("created_by", sa.UUID(), nullable=True))
    op.add_column("schedules", sa.Column("updated_by", sa.UUID(), nullable=True))
    op.create_foreign_key(None, "schedules", "users", ["created_by"], ["id"])
    op.create_foreign_key(None, "schedules", "users", ["updated_by"], ["id"])

    op.create_index(
        "uq_open_personal_episode",
        "personal_episodes",
        ["user_id", "location_id"],
        unique=True,
        postgresql_where=sa.text("is_open"),
    )
    op.create_check_constraint(
        "personal_episode_interval",
        "personal_episodes",
        "ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at",
    )


def downgrade():
    if (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM notices WHERE published_at IS NULL"))
        .scalar()
    ):
        raise RuntimeError(
            "Downgrade refused: unknown publication times cannot fit schema 0002"
        )
    op.drop_index("uq_open_personal_episode", table_name="personal_episodes")
    op.drop_constraint("personal_episode_interval", "personal_episodes", type_="check")
    op.drop_constraint("schedules_updated_by_fkey", "schedules", type_="foreignkey")
    op.drop_constraint("schedules_created_by_fkey", "schedules", type_="foreignkey")
    op.drop_column("schedules", "updated_by")
    op.drop_column("schedules", "created_by")
    op.drop_column("schedules", "is_demo")
    op.drop_column("schedules", "coverage_scope")
    op.drop_column("schedules", "coverage")
    op.drop_column("schedules", "category")
    op.drop_column("schedules", "version")
    op.drop_column("schedules", "lifecycle")
    op.drop_constraint("reports_candidate_event_id_fkey", "reports", type_="foreignkey")
    op.drop_constraint("reports_episode_id_fkey", "reports", type_="foreignkey")
    op.drop_column("reports", "candidate_event_id")
    op.drop_column("reports", "episode_id")
    op.drop_column("reports", "is_demo")
    op.drop_column("reports", "moderation")
    op.drop_column("reports", "note")
    op.drop_constraint("notices_updated_by_fkey", "notices", type_="foreignkey")
    op.drop_constraint("notices_created_by_fkey", "notices", type_="foreignkey")
    op.execute(
        "UPDATE notices SET published_at = created_at WHERE published_at IS NULL"
    )
    op.alter_column(
        "notices",
        "published_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
    )
    op.drop_column("notices", "updated_by")
    op.drop_column("notices", "created_by")
    op.drop_column("notices", "version")
    op.drop_column("notices", "is_demo")
    op.drop_column("notices", "lifecycle")
    op.drop_index(op.f("ix_personal_episodes_user_id"), table_name="personal_episodes")
    op.drop_table("personal_episodes")
    op.drop_index(op.f("ix_evidence_audit_entity_id"), table_name="evidence_audit")
    op.drop_table("evidence_audit")
