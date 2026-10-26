"""Operational API. Demo fixtures are never queried by these endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session
from .db import get_db
from .models import Location, Notice, OutageEvent, Report, SavedArea, Schedule, User
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
        "id": r.id,
        "parent_id": r.parent_id,
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
    search: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Location)
    if parent_id:
        stmt = stmt.where(Location.parent_id == parent_id)
    if search:
        stmt = stmt.where(
            or_(
                Location.name_bn.ilike("%" + search + "%"),
                Location.name_en.ilike("%" + search + "%"),
            )
        )
    return list_page(
        db, stmt.order_by(Location.name_en, Location.id), page, page_size, loc_json
    )


@router.post("/admin/locations", status_code=201)
def create_location(
    body: LocationInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    parent = find(db, Location, body.parent_id) if body.parent_id else None
    if (parent.kind if parent else None) not in KINDS[body.kind]:
        raise HTTPException(422, "Invalid location parent")
    if db.scalar(select(Location.id).where(Location.slug == body.slug)):
        raise HTTPException(409, "Slug already exists")
    item = Location(**body.model_dump(), verification_status="unverified")
    db.add(item)
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
    item = find(db, Location, location_id)
    parent = find(db, Location, body.parent_id) if body.parent_id else None
    if (parent.kind if parent else None) not in KINDS[body.kind]:
        raise HTTPException(422, "Invalid location parent")
    cursor = parent
    while cursor:
        if cursor.id == item.id:
            raise HTTPException(422, "Location cycle")
        cursor = db.get(Location, cursor.parent_id) if cursor.parent_id else None
    if db.scalar(
        select(Location.id).where(Location.slug == body.slug, Location.id != item.id)
    ):
        raise HTTPException(409, "Slug already exists")
    for k, v in body.model_dump().items():
        setattr(item, k, v)
    item.verification_status = "unverified"
    item.source_url = None
    item.verified_at = None
    db.execute(
        update(Schedule)
        .where(Schedule.location_id == item.id, Schedule.status == "announced")
        .values(status="superseded")
    )
    db.commit()
    db.refresh(item)
    return loc_json(item)


class VerifyInput(BaseModel):
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
    item = find(db, Location, location_id)
    item.source_url = str(body.source_url)
    item.verified_at = now()
    item.verification_status = "verified"
    db.commit()
    db.refresh(item)
    return loc_json(item)


@router.delete("/admin/locations/{location_id}", status_code=204)
def delete_location(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = find(db, Location, location_id)
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
        ]
    ):
        raise HTTPException(409, "Location is in use")
    db.delete(item)
    db.commit()


@router.get("/notices")
def notices(
    db: Session = Depends(get_db),
    search: str | None = Query(None, max_length=100),
    status: Literal["unverified", "verified", "rejected"] | None = None,
    sort: Literal["newest", "oldest"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Notice)
    if search:
        stmt = stmt.where(Notice.title.ilike("%" + search + "%"))
    if status:
        stmt = stmt.where(Notice.verification_status == status)
    order = (
        Notice.published_at.desc() if sort == "newest" else Notice.published_at.asc()
    )
    return list_page(db, stmt.order_by(order, Notice.id), page, page_size, notice_json)


@router.post("/admin/notices", status_code=201)
def create_notice(
    body: NoticeInput, db: Session = Depends(get_db), admin: User = Depends(admin_user)
):
    item = Notice(
        **{**body.model_dump(), "source_url": str(body.source_url)},
        verification_status="unverified",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return notice_json(item)


@router.put("/admin/notices/{notice_id}")
def edit_notice(
    notice_id: uuid.UUID,
    body: NoticeInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = find(db, Notice, notice_id)
    for k, v in body.model_dump().items():
        setattr(item, k, str(v) if k == "source_url" else v)
    item.verification_status = "unverified"
    item.verified_by = None
    item.verified_at = None
    db.execute(
        update(Schedule)
        .where(Schedule.notice_id == item.id, Schedule.status == "announced")
        .values(status="superseded")
    )
    db.commit()
    db.refresh(item)
    return notice_json(item)


@router.post("/admin/notices/{notice_id}/verify")
def verify_notice(
    notice_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = find(db, Notice, notice_id)
    if not item.source_url:
        raise HTTPException(422, "Original source required")
    item.verification_status = "verified"
    item.verified_by = admin.id
    item.verified_at = now()
    db.commit()
    db.refresh(item)
    return notice_json(item)


@router.delete("/admin/notices/{notice_id}", status_code=204)
def delete_notice(
    notice_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = find(db, Notice, notice_id)
    if db.scalar(select(Schedule.id).where(Schedule.notice_id == item.id)):
        raise HTTPException(409, "Notice has schedules")
    db.delete(item)
    db.commit()


@router.get("/schedules")
def schedules(
    db: Session = Depends(get_db),
    location_id: uuid.UUID | None = None,
    status: Literal["announced", "cancelled", "superseded"] | None = None,
    sort: Literal["newest", "oldest"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Schedule)
    if location_id:
        stmt = stmt.where(Schedule.location_id == location_id)
    if status:
        stmt = stmt.where(Schedule.status == status)
    order = Schedule.starts_at.desc() if sort == "newest" else Schedule.starts_at.asc()
    return list_page(
        db, stmt.order_by(order, Schedule.id), page, page_size, schedule_json
    )


@router.post("/admin/schedules", status_code=201)
def create_schedule(
    body: ScheduleInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    notice = find(db, Notice, body.notice_id)
    loc = find(db, Location, body.location_id)
    if (
        notice.verification_status != "verified"
        or loc.verification_status != "verified"
    ):
        raise HTTPException(422, "Verified notice and area required")
    if body.ends_at <= body.starts_at:
        raise HTTPException(422, "End must follow start")
    item = Schedule(**body.model_dump(), status="announced")
    db.add(item)
    db.commit()
    db.refresh(item)
    return schedule_json(item)


@router.put("/admin/schedules/{schedule_id}")
def edit_schedule(
    schedule_id: uuid.UUID,
    body: ScheduleInput,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = find(db, Schedule, schedule_id)
    notice = find(db, Notice, body.notice_id)
    loc = find(db, Location, body.location_id)
    if (
        notice.verification_status != "verified"
        or loc.verification_status != "verified"
        or body.ends_at <= body.starts_at
    ):
        raise HTTPException(422, "Verified evidence and valid interval required")
    for k, v in body.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return schedule_json(item)


@router.post("/admin/schedules/{schedule_id}/cancel")
def cancel_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = find(db, Schedule, schedule_id)
    item.status = "cancelled"
    db.commit()
    db.refresh(item)
    return schedule_json(item)


@router.delete("/admin/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    item = find(db, Schedule, schedule_id)
    db.delete(item)
    db.commit()


@router.get("/saved-areas")
def saved_areas(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(
        select(Location)
        .join(SavedArea, SavedArea.location_id == Location.id)
        .where(SavedArea.user_id == user.id)
        .order_by(Location.name_bn)
    ).all()
    return {"items": [loc_json(r) for r in rows]}


@router.post("/saved-areas/{location_id}", status_code=201)
def save_area(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    loc = find(db, Location, location_id)
    if loc.verification_status != "verified":
        raise HTTPException(422, "Area is not verified")
    if not db.get(SavedArea, {"user_id": user.id, "location_id": location_id}):
        db.add(SavedArea(user_id=user.id, location_id=location_id))
        db.commit()
    return {"saved": True}


@router.delete("/saved-areas/{location_id}", status_code=204)
def unsave_area(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    entry = db.get(SavedArea, {"user_id": user.id, "location_id": location_id})
    if entry:
        db.delete(entry)
        db.commit()


@router.get("/reports")
def reports(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    find(db, Location, location_id)
    return list_page(
        db,
        select(Report)
        .where(Report.location_id == location_id)
        .order_by(Report.observed_at.desc(), Report.id.desc()),
        page,
        page_size,
        report_json,
    )


@router.post("/reports", status_code=201)
def create_report(
    body: ReportInput, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    loc = find(db, Location, body.location_id)
    if loc.verification_status != "verified":
        raise HTTPException(422, "Area is not verified")
    existing = db.scalar(
        select(Report).where(
            Report.user_id == user.id, Report.idempotency_key == body.idempotency_key
        )
    )
    if existing:
        if existing.location_id != body.location_id or existing.kind != body.kind:
            raise HTTPException(409, "Request key reused for different report")
        return report_json(existing)
    instant = now()
    if (
        not instant - timedelta(hours=24)
        <= body.observed_at
        <= instant + timedelta(minutes=5)
    ):
        raise HTTPException(422, "Observation time outside allowed window")
    recent = db.scalar(
        select(Report)
        .where(
            Report.user_id == user.id,
            Report.location_id == loc.id,
            Report.kind == body.kind,
            Report.observed_at >= instant - timedelta(minutes=10),
        )
        .order_by(Report.observed_at.desc())
        .limit(1)
    )
    if recent:
        raise HTTPException(429, "Similar report submitted recently")
    item = Report(user_id=user.id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return report_json(item)


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
    item = find(db, OutageEvent, event_id)
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


@router.post("/activities/check")
def activity_conflicts(body: ActivityInput, db: Session = Depends(get_db)):
    find(db, Location, body.location_id)
    if body.ends_at <= body.starts_at or body.ends_at - body.starts_at > timedelta(
        days=7
    ):
        raise HTTPException(
            422, "Activity interval must be positive and at most seven days"
        )
    rows = db.scalars(
        select(Schedule)
        .join(Notice, Notice.id == Schedule.notice_id)
        .join(Location, Location.id == Schedule.location_id)
        .where(
            Schedule.location_id == body.location_id,
            Schedule.status == "announced",
            Notice.verification_status == "verified",
            Location.verification_status == "verified",
            Schedule.starts_at < body.ends_at,
            Schedule.ends_at > body.starts_at,
        )
        .order_by(Schedule.starts_at)
    ).all()
    return {
        "conflicts": [schedule_json(s) for s in rows],
        "message": "No announced conflict found; power availability is not guaranteed."
        if not rows
        else "Activity overlaps an announced outage; actual interruption may differ.",
    }
