"""Reviewed electricity offices and explicit feeder coverage claims; no seeded data."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = depends_on = None


def common():
    return [
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
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(20),
            server_default="unverified",
            nullable=False,
        ),
        sa.Column("verified_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    ]


def upgrade():
    op.create_table(
        "electricity_offices",
        *common(),
        sa.Column("name_bn", sa.String(160), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.CheckConstraint(
            "verification_status IN ('unverified','verified')", name="office_status"
        ),
        sa.CheckConstraint(
            "verification_status != 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)",
            name="office_evidence",
        ),
    )
    op.create_index(
        "uq_office_name",
        "electricity_offices",
        [sa.text("lower(btrim(name_en))")],
        unique=True,
    )
    op.create_table(
        "feeder_mappings",
        *common(),
        sa.Column(
            "office_id",
            UUID(as_uuid=True),
            sa.ForeignKey("electricity_offices.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("feeder_name", sa.String(160), nullable=False),
        sa.Column("coverage_description", sa.String(1000), nullable=False),
        sa.CheckConstraint(
            "verification_status IN ('unverified','verified')",
            name="feeder_mapping_status",
        ),
        sa.CheckConstraint(
            "verification_status != 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)",
            name="feeder_mapping_evidence",
        ),
    )
    op.create_index("ix_feeder_mappings_office_id", "feeder_mappings", ["office_id"])
    op.create_index(
        "ix_feeder_mappings_location_id", "feeder_mappings", ["location_id"]
    )
    op.create_index(
        "uq_feeder_mapping",
        "feeder_mappings",
        ["office_id", "location_id", sa.text("lower(btrim(feeder_name))")],
        unique=True,
    )


def downgrade():
    op.drop_table("feeder_mappings")
    op.drop_table("electricity_offices")
