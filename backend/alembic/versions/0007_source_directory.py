"""Keep supplied portal and historical census snapshots separate, with provenance."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = depends_on = None


def common():
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade():
    op.drop_index("uq_location_en", table_name="locations")
    op.alter_column("locations", "name_en", existing_type=sa.String(160), nullable=True)
    op.create_index(
        "uq_location_en",
        "locations",
        ["parent_id", "kind", sa.text("lower(btrim(name_en))")],
        unique=True,
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("name_en IS NOT NULL"),
    )
    op.create_table(
        "directory_datasets",
        *common(),
        sa.Column("checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("sources", JSONB(), nullable=False),
        sa.Column("review", JSONB(), nullable=False),
        sa.Column("ancillary", JSONB(), nullable=False),
    )
    op.create_table(
        "directory_places",
        *common(),
        sa.Column(
            "dataset_id",
            UUID(as_uuid=True),
            sa.ForeignKey("directory_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("branch", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("directory_places.id", ondelete="RESTRICT"),
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name_bn", sa.String(160)),
        sa.Column("name_en", sa.String(160)),
        sa.Column("aliases", JSONB(), nullable=False),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column(
            "location_id",
            UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="SET NULL"),
        ),
        sa.Column("original", JSONB(), nullable=False),
        sa.UniqueConstraint(
            "dataset_id", "branch", "external_id", name="uq_directory_identity"
        ),
        sa.CheckConstraint(
            "branch IN ('portal','census2022')", name="directory_branch"
        ),
        sa.CheckConstraint(
            "review_status IN ('source_checked','needs_review','historical')",
            name="directory_review",
        ),
        sa.CheckConstraint(
            "name_bn IS NOT NULL OR name_en IS NOT NULL", name="directory_name"
        ),
        sa.CheckConstraint(
            "branch != 'census2022' OR location_id IS NULL",
            name="census_not_current_location",
        ),
    )
    for field in ["dataset_id", "parent_id", "location_id"]:
        op.create_index("ix_directory_places_" + field, "directory_places", [field])


def downgrade():
    # Do not manufacture English names or erase a supplied directory to downgrade.
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM directory_places) OR EXISTS(SELECT 1 FROM locations WHERE name_en IS NULL)"
        )
    ).scalar_one():
        raise RuntimeError(
            "Export/reconcile directory records and missing English names before downgrade; no records removed"
        )
    op.drop_table("directory_places")
    op.drop_table("directory_datasets")
    op.drop_index("uq_location_en", table_name="locations")
    op.alter_column(
        "locations", "name_en", existing_type=sa.String(160), nullable=False
    )
    op.create_index(
        "uq_location_en",
        "locations",
        ["parent_id", "kind", sa.text("lower(btrim(name_en))")],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
