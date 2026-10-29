"""Operational API. Demo fixtures are never queried by these endpoints."""

import unicodedata
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import String, cast, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    Activity,
    FeederMapping,
    Location,
    OutageEvent,
    PersonalEpisode,
    Report,
    SavedArea,
    Schedule,
    User,
)
from .security import admin_user, current_user, now

router = APIRouter(prefix="/api", tags=["operational data"])
KINDS = {
    "division": {None},
    "district": {"division"},
    "upazila": {"district"},
    "city_corporation": {"district"},
    "union": {"upazila"},
    "ward": {"city_corporation"},
    "village": {"union"},
    "neighborhood": {"ward", "village"},
}


def aware(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone offset required")
    return value


class Page(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class LocationInput(BaseModel):
    version: int = Field(default=1, ge=1)
    aliases: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, values):
        aliases = list(
            dict.fromkeys(
                " ".join(unicodedata.normalize("NFKC", v).split()) for v in values
            )
        )
        if any(not 2 <= len(v) <= 160 for v in aliases):
            raise ValueError("Aliases must contain 2–160 characters")
        return aliases

    @field_validator("name_bn", "name_en", check_fields=False)
    @classmethod
    def normalize_name(cls, value):
        result = " ".join(unicodedata.normalize("NFKC", value).split())
        if not 2 <= len(result) <= 160:
            raise ValueError("Normalized name must contain 2–160 characters")
        return result

    name_bn: str = Field(min_length=2, max_length=160)
    name_en: str = Field(min_length=2, max_length=160)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=180)
    kind: Literal[
        "division",
        "district",
        "upazila",
        "city_corporation",
        "union",
        "ward",
        "village",
        "neighborhood",
    ]
    parent_id: uuid.UUID | None = None


class NoticeInput(BaseModel):
    title: str = Field(min_length=4, max_length=240)
    body: str = Field(min_length=10, max_length=10000)
    source_url: HttpUrl
    publisher: str = Field(min_length=2, max_length=160)
    published_at: datetime

    @field_validator("source_url")
    @classmethod
    def https_source(cls, v):
        if v.scheme != "https":
            raise ValueError("HTTPS source required")
        return v

    @field_validator("published_at")
    @classmethod
    def check_time(cls, v):
        return aware(v)


class ScheduleInput(BaseModel):
    notice_id: uuid.UUID
    location_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime

    @field_validator("starts_at", "ends_at")
    @classmethod
    def check_time(cls, v):
        return aware(v)


class ReportInput(BaseModel):
    location_id: uuid.UUID
    kind: Literal["power_off", "power_back", "still_off"]
    observed_at: datetime
    idempotency_key: uuid.UUID

    @field_validator("observed_at")
    @classmethod
    def check_time(cls, v):
        return aware(v)


class EventInput(BaseModel):
    location_id: uuid.UUID
    started_at: datetime
    start_evidence: str = Field(min_length=12, max_length=2000)

    @field_validator("started_at")
    @classmethod
    def check_time(cls, v):
        return aware(v)


class RestorationInput(BaseModel):
    version: int = Field(default=1, ge=1)
    restored_at: datetime
    evidence: str = Field(min_length=12, max_length=2000)

    @field_validator("restored_at")
    @classmethod
    def check_time(cls, v):
        return aware(v)


class ActivityInput(BaseModel):
    location_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime

    @field_validator("starts_at", "ends_at")
    @classmethod
    def check_time(cls, v):
        return aware(v)


def find(db, model, key):
    item = db.get(model, key)
    if not item:
        raise HTTPException(404, "Record not found")
    return item


def list_page(db, stmt, page: int, size: int, render):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset((page - 1) * size).limit(size)).all()
    return {
        "items": [render(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": size,
    }


def loc_json(r):
    return {
        "version": r.version,
        "id": r.id,
        "parent_id": r.parent_id,
        "aliases": r.aliases,
        "kind": r.kind,
        "name_bn": r.name_bn,
        "name_en": r.name_en,
        "slug": r.slug,
        "verification_status": r.verification_status,
        "source_url": r.source_url,
        "verified_at": r.verified_at,
        "updated_at": r.updated_at,
    }


def notice_json(r):
    return {
        "id": r.id,
        "title": r.title,
        "body": r.body,
        "source_url": r.source_url,
        "publisher": r.publisher,
        "published_at": r.published_at,
        "verification_status": r.verification_status,
        "verified_at": r.verified_at,
        "updated_at": r.updated_at,
    }


def schedule_json(r):
    return {
        "id": r.id,
        "notice_id": r.notice_id,
        "location_id": r.location_id,
        "starts_at": r.starts_at,
        "ends_at": r.ends_at,
        "status": r.status,
        "updated_at": r.updated_at,
    }


def report_json(r):
    return {
        "id": r.id,
        "location_id": r.location_id,
        "kind": r.kind,
        "observed_at": r.observed_at,
        "created_at": r.created_at,
        "scope": "individual_connection",
    }


def event_json(r):
    return {
        "version": r.version,
        "id": r.id,
        "location_id": r.location_id,
        "started_at": r.started_at,
        "restored_at": r.restored_at,
        "start_evidence": r.start_evidence,
        "restoration_evidence": r.restoration_evidence,
        "verified_at": r.verified_at,
        "updated_at": r.updated_at,
    }


@router.get("/locations")
def locations(
    db: Session = Depends(get_db),
    parent_id: uuid.UUID | None = None,
    roots_only: bool = False,
    kind: str | None = None,
    status: Literal["verified", "unverified"] | None = None,
    search: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Location)
    if roots_only:
        stmt = stmt.where(Location.parent_id.is_(None))
    if kind:
        if kind not in KINDS:
            raise HTTPException(422, "Invalid location type")
        stmt = stmt.where(Location.kind == kind)
    if status:
        stmt = stmt.where(Location.verification_status == status)
    if parent_id:
        stmt = stmt.where(Location.parent_id == parent_id)
    if search:
        predicates = [
            Location.name_bn.ilike("%" + search + "%"),
            Location.name_en.ilike("%" + search + "%"),
            cast(Location.aliases, String).ilike("%" + search + "%"),
        ]
        try:
            predicates.append(Location.id == uuid.UUID(search))
        except ValueError:
            pass
        stmt = stmt.where(or_(*predicates))

    result = list_page(
        db, stmt.order_by(Location.name_en, Location.id), page, page_size, loc_json
    )
    ids = [r["id"] for r in result["items"]]
    paths = {key: [] for key in ids}
    if ids:
        rows = db.execute(
            text("""
            WITH RECURSIVE ancestors AS (
                SELECT id AS origin, id, parent_id, name_bn, 0 AS depth, ARRAY[id] AS visited
                FROM locations WHERE id = ANY(:ids)
                UNION ALL
                SELECT a.origin,p.id,p.parent_id,p.name_bn,a.depth+1,a.visited || p.id
                FROM locations p JOIN ancestors a ON p.id=a.parent_id
                WHERE NOT p.id = ANY(a.visited)
            ) SELECT origin,name_bn FROM ancestors WHERE depth > 0 ORDER BY depth DESC
        """),
            {"ids": ids},
        )
        for origin, name in rows:
            paths[origin].append(name)
    for item in result["items"]:
        item["ancestor_names"] = paths[item["id"]]
    return result


@router.post("/admin/locations", status_code=201)
def create_location(
    body: LocationInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    db.execute(text("SELECT pg_advisory_xact_lock(34001)"))
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    parent = find(db, Location, body.parent_id) if body.parent_id else None
    if (parent.kind if parent else None) not in KINDS[body.kind]:
        raise HTTPException(422, "Invalid location parent")
    if db.scalar(select(Location.id).where(Location.slug == body.slug)):
        raise HTTPException(409, "Slug already exists")
    item = Location(
        **body.model_dump(exclude={"version"}), verification_status="unverified"
    )
    db.add(item)
    db.flush()
    from .evidence import audit

    audit(db, admin, item, "create")
    db.commit()
    db.refresh(item)
    return loc_json(item)


@router.put("/admin/locations/{location_id}")
def edit_location(
    location_id: uuid.UUID,
    body: LocationInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    db.execute(text("SELECT pg_advisory_xact_lock(34001)"))
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    item = find(db, Location, location_id)
    if item.version != body.version:
        raise HTTPException(409, "Location changed; reload before editing")
    parent = find(db, Location, body.parent_id) if body.parent_id else None
    if (parent.kind if parent else None) not in KINDS[body.kind]:
        raise HTTPException(422, "Invalid location parent")
    children = db.scalars(select(Location).where(Location.parent_id == item.id)).all()
    if any(body.kind not in KINDS[child.kind] for child in children):
        raise HTTPException(422, "Change would invalidate existing children")
    cursor = parent
    while cursor:
        if cursor.id == item.id:
            raise HTTPException(422, "Location cycle")
        cursor = db.get(Location, cursor.parent_id) if cursor.parent_id else None
    if db.scalar(
        select(Location.id).where(Location.slug == body.slug, Location.id != item.id)
    ):
        raise HTTPException(409, "Slug already exists")
    for k, v in body.model_dump(exclude={"version"}).items():
        setattr(item, k, v)
    item.version += 1
    item.verification_status = "unverified"
    from .registry import invalidate_location_mappings

    invalidate_location_mappings(db, item.id)
    item.source_url = None
    item.verified_at = None
    for schedule in db.scalars(
        select(Schedule)
        .where(
            or_(
                Schedule.location_id == item.id,
                Schedule.coverage.contains([{"id": str(item.id)}]),
            ),
            Schedule.status == "announced",
        )
        .with_for_update()
    ):
        schedule.status = "superseded"
        schedule.version += 1
    db.commit()
    db.refresh(item)
    return loc_json(item)


class VerifyInput(BaseModel):
    version: int = Field(default=1, ge=1)
    source_url: HttpUrl

    @field_validator("source_url")
    @classmethod
    def https_source(cls, v):
        if v.scheme != "https":
            raise ValueError("HTTPS source required")
        return v


@router.post("/admin/locations/{location_id}/verify")
def verify_location(
    location_id: uuid.UUID,
    body: VerifyInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    db.execute(text("SELECT pg_advisory_xact_lock(34001)"))
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    item = find(db, Location, location_id)
    if item.version != body.version:
        raise HTTPException(409, "Location changed; reload before verification")
    item.version += 1
    item.source_url = str(body.source_url)
    item.verified_at = now()
    item.verification_status = "verified"
    db.commit()
    db.refresh(item)
    return loc_json(item)


@router.delete("/admin/locations/{location_id}", status_code=204)
def delete_location(
    location_id: uuid.UUID,
    version: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    db.execute(text("SELECT pg_advisory_xact_lock(34001)"))
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    item = db.scalar(
        select(Location).where(Location.id == location_id).with_for_update()
    )
    if not item:
        raise HTTPException(404, "Record not found")
    if item.version != version:
        raise HTTPException(409, "Location changed; reload before deleting")
    if db.scalar(
        select(Schedule.id)
        .where(
            or_(
                Schedule.coverage.contains([{"id": str(location_id)}]),
                Schedule.coverage.contains([{"ancestor_ids": [str(location_id)]}]),
            )
        )
        .limit(1)
    ):
        raise HTTPException(409, "Location is referenced by schedule coverage")
    if any(
        db.scalar(
            select(model.id if hasattr(model, "id") else model.user_id).where(
                column == location_id
            )
        )
        for model, column in [
            (Location, Location.parent_id),
            (Schedule, Schedule.location_id),
            (Report, Report.location_id),
            (OutageEvent, OutageEvent.location_id),
            (SavedArea, SavedArea.location_id),
            (Activity, Activity.location_id),
            (FeederMapping, FeederMapping.location_id),
            (PersonalEpisode, PersonalEpisode.location_id),
        ]
    ):
        raise HTTPException(409, "Location is in use")
    db.delete(item)
    db.commit()


class SavedAreaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(default="", max_length=60)
    is_default: bool = False


@router.get("/saved-areas")
def saved_areas(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.execute(
        select(Location, SavedArea)
        .join(SavedArea, SavedArea.location_id == Location.id)
        .where(SavedArea.user_id == user.id)
        .order_by(SavedArea.is_default.desc(), Location.name_bn, Location.id)
    ).all()
    return {
        "items": [
            loc_json(loc)
            | {
                "label": saved.label,
                "is_default": saved.is_default,
                "available": loc.verification_status == "verified",
            }
            for loc, saved in rows
        ]
    }


@router.post("/saved-areas/{location_id}", status_code=201)
def save_area(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    loc = find(db, Location, location_id)
    if loc.verification_status != "verified":
        raise HTTPException(422, "Area is not verified")
    inserted = db.execute(
        insert(SavedArea)
        .values(user_id=user.id, location_id=location_id)
        .on_conflict_do_nothing()
        .returning(SavedArea.location_id)
    ).scalar_one_or_none()
    db.commit()
    return {"saved": True, "already_saved": inserted is None}


@router.put("/saved-areas/{location_id}")
def update_saved_area(
    location_id: uuid.UUID,
    body: SavedAreaInput,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    entry = db.get(SavedArea, {"user_id": user.id, "location_id": location_id})
    if entry is None:
        raise HTTPException(404, "Saved area not found")
    loc = find(db, Location, location_id)
    if body.is_default and loc.verification_status != "verified":
        raise HTTPException(422, "Default area is unavailable")
    if body.is_default:
        db.execute(
            update(SavedArea)
            .where(SavedArea.user_id == user.id, SavedArea.location_id != location_id)
            .values(is_default=False)
        )
    entry.is_default = body.is_default
    entry.label = body.label.strip()
    db.commit()
    return {"saved": True, "label": entry.label, "is_default": entry.is_default}


@router.delete("/saved-areas/{location_id}", status_code=204)
def unsave_area(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    entry = db.get(SavedArea, {"user_id": user.id, "location_id": location_id})
    if entry:
        db.delete(entry)
    db.commit()


@router.get("/events")
def events(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    find(db, Location, location_id)
    return list_page(
        db,
        select(OutageEvent)
        .where(OutageEvent.location_id == location_id)
        .order_by(OutageEvent.started_at.desc(), OutageEvent.id.desc()),
        page,
        page_size,
        event_json,
    )


@router.post("/admin/events", status_code=201)
def create_event(
    body: EventInput, db: Session = Depends(get_db), admin: User = Depends(admin_user)
):
    loc = find(db, Location, body.location_id)
    if loc.verification_status != "verified" or body.started_at > now():
        raise HTTPException(422, "Verified area and past start required")
    item = OutageEvent(**body.model_dump(), verified_by=admin.id, verified_at=now())
    db.add(item)
    db.flush()
    from .evidence import audit

    audit(db, admin, item, "create")
    db.commit()
    db.refresh(item)
    return event_json(item)


@router.post("/admin/events/{event_id}/restore")
def restore(
    event_id: uuid.UUID,
    body: RestorationInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = db.scalar(
        select(OutageEvent).where(OutageEvent.id == event_id).with_for_update()
    )
    if not item:
        raise HTTPException(404, "Event not found")
    if item.version != body.version:
        raise HTTPException(409, "Event changed; reload before editing")
    item.version += 1
    if item.restored_at:
        raise HTTPException(409, "Event already restored")
    if not item.started_at <= body.restored_at <= now():
        raise HTTPException(422, "Invalid restoration time")
    item.restored_at = body.restored_at
    item.restoration_evidence = body.evidence
    item.verified_by = admin.id
    item.verified_at = now()
    db.commit()
    db.refresh(item)
    return event_json(item)


@router.get("/locations/{location_id}")
def location_detail(location_id: uuid.UUID, db: Session = Depends(get_db)):
    return loc_json(find(db, Location, location_id))


@router.get("/locations/{location_id}/ancestors")
def location_ancestors(location_id: uuid.UUID, db: Session = Depends(get_db)):
    node = find(db, Location, location_id)
    items = []
    seen = {node.id}
    while node.parent_id:
        node = find(db, Location, node.parent_id)
        if node.id in seen:
            raise HTTPException(409, "Invalid location hierarchy")
        seen.add(node.id)
        items.append(loc_json(node))
    return {"items": list(reversed(items))}


@router.get("/locations/{location_id}/children")
def location_children(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    find(db, Location, location_id)
    return list_page(
        db,
        select(Location)
        .where(Location.parent_id == location_id)
        .order_by(Location.name_en, Location.id),
        page,
        page_size,
        loc_json,
    )


class DeactivateLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=500)


@router.post("/admin/locations/{location_id}/deactivate")
def deactivate_location(
    location_id: uuid.UUID,
    body: DeactivateLocation,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    """Suspend verification; keep evidence/references and historical observations."""
    db.execute(text("SELECT pg_advisory_xact_lock(34001)"))
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    item = find(db, Location, location_id)
    if item.version != body.version:
        raise HTTPException(409, "Location changed; reload before deactivating")
    db.info["audit_reason"] = body.reason
    item.version += 1
    item.verification_status = "unverified"
    from .registry import invalidate_location_mappings

    invalidate_location_mappings(db, item.id)
    for schedule in db.scalars(
        select(Schedule)
        .where(
            or_(
                Schedule.location_id == item.id,
                Schedule.coverage.contains([{"id": str(item.id)}]),
            ),
            Schedule.status == "announced",
        )
        .with_for_update()
    ):
        schedule.status = "superseded"
        schedule.version += 1
    db.commit()
    return loc_json(item)
