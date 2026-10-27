"""Domain storage; authorization and cross-record validation belong in upcoming services."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Record:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Location(Record, Base):
    __tablename__ = "locations"
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    name_bn: Mapped[str] = mapped_column(String(160))
    name_en: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(32))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index(
            "uq_location_bn",
            parent_id,
            kind,
            func.lower(func.btrim(name_bn)),
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "uq_location_en",
            parent_id,
            kind,
            func.lower(func.btrim(name_en)),
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "kind IN ('division','district','upazila','city_corporation','union','ward','village','neighborhood')",
            name="location_kind",
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id != id", name="location_not_self"
        ),
        CheckConstraint(
            "verification_status IN ('unverified','verified')",
            name="location_verification",
        ),
        CheckConstraint(
            "verification_status != 'verified' OR (source_url IS NOT NULL AND verified_at IS NOT NULL)",
            name="location_evidence",
        ),
    )


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("role IN ('admin','user')", name="user_role"),
        Index("uq_user_normalized_email", func.lower(func.btrim(email)), unique=True),
    )


class SavedArea(Base):
    __tablename__ = "saved_areas"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )


class RefreshSession(Record, Base):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "refresh_sessions.id",
            ondelete="SET NULL",
            name="refresh_sessions_replaced_by_id_fkey",
        )
    )


class PasswordReset(Record, Base):
    __tablename__ = "password_resets"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notice(Record, Base):
    __tablename__ = "notices"
    title: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(160))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified','verified','rejected')",
            name="notice_verification",
        ),
        CheckConstraint(
            "verification_status != 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)",
            name="notice_evidence",
        ),
    )


class Schedule(Record, Base):
    __tablename__ = "schedules"
    notice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notices.id", ondelete="RESTRICT"), index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="announced")
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="schedule_interval"),
        CheckConstraint(
            "status IN ('announced','cancelled','superseded')", name="schedule_status"
        ),
    )


class Report(Record, Base):
    __tablename__ = "reports"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    __table_args__ = (
        CheckConstraint(
            "kind IN ('power_off','power_back','still_off')", name="report_kind"
        ),
        UniqueConstraint("user_id", "idempotency_key", name="report_idempotency"),
    )


class OutageEvent(Record, Base):
    __tablename__ = "outage_events"
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_evidence: Mapped[str] = mapped_column(Text)
    restoration_evidence: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint(
            "restored_at IS NULL OR restored_at >= started_at", name="event_interval"
        ),
        CheckConstraint(
            "restored_at IS NULL OR restoration_evidence IS NOT NULL",
            name="restoration_requires_evidence",
        ),
    )


class DemoArea(Record, Base):
    """Physically separate fixture table; never joined to operational records."""

    __tablename__ = "demo_areas"
    name_bn: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
