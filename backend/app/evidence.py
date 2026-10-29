"""Sections 5–6: published evidence and per-connection observations."""

import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import String, func, or_, select, text
from sqlalchemy.orm import Session

from .api import NoticeInput, ReportInput, ScheduleInput, aware, find, list_page
from .config import get_settings
from .db import get_db
from .models import (
    EvidenceAudit,
    Location,
    Notice,
    OutageEvent,
    PersonalEpisode,
    Report,
    Schedule,
    User,
)
from .security import admin_user, current_user, now

router = APIRouter(prefix="/api", tags=["notices and observations"])


def serialize(item):
    return {c.name: getattr(item, c.name) for c in item.__table__.columns}


def report_json(r):
    return {
        k: v
        for k, v in serialize(r).items()
        if k not in {"user_id", "idempotency_key", "note", "candidate_event_id"}
    } | {"scope": "individual_connection"}


def audit(db, actor, item, action):
    db.add(
        EvidenceAudit(
            actor_id=actor.id,
            entity_id=item.id,
            entity_type=item.__tablename__,
            action=action,
            snapshot=jsonable_encoder(serialize(item)),
        )
    )


def locked(db, model, key, version):
    item = db.scalar(select(model).where(model.id == key).with_for_update())
    if not item:
        raise HTTPException(404, "Record not found")
    if version != item.version:
        raise HTTPException(409, "Record changed; reload before editing")
    return item


class NoticeBody(NoticeInput):
    model_config = ConfigDict(extra="forbid")
    published_at: datetime | None = None
    version: int = Field(default=1, ge=1)
    is_demo: bool = False

    @field_validator("published_at")
    @classmethod
    def check_time(cls, value):
        return aware(value) if value else None


class ScheduleBody(ScheduleInput):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(default=1, ge=1)
    location_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    category: str = Field(default="maintenance", min_length=2, max_length=100)
    coverage_scope: Literal["named_locations", "entire_administrative_area"] = (
        "named_locations"
    )
    feeder_id: uuid.UUID | None = None


class VersionBody(BaseModel):
    reason: str = Field(default="", max_length=500)
    version: int = Field(ge=1)


# All public queries deliberately exclude drafts and demo records.
def visible_notice():
    return (
        Notice.lifecycle == "published",
        Notice.verification_status == "verified",
        Notice.is_demo.is_(False),
    )


@router.get("/notices")
def notice_list(
    db: Session = Depends(get_db),
    search: str = Query("", max_length=240),
    status: Literal["verified", "unverified", "rejected"] | None = None,
    location_id: uuid.UUID | None = None,
    category: str | None = None,
    feeder: str | None = None,
    office: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: Literal["newest", "oldest"] = "newest",
):
    # Private listings are implemented separately below; public input cannot grant access.
    stmt = select(Notice).where(*visible_notice())
    if location_id or category:
        covered = select(Schedule.notice_id)
        if location_id:
            covered = covered.where(
                or_(
                    Schedule.location_id == location_id,
                    Schedule.coverage.contains([{"id": str(location_id)}]),
                )
            )
        if category:
            covered = covered.where(Schedule.category == category)
        stmt = stmt.where(Notice.id.in_(covered))
    if feeder:
        stmt = stmt.where(False)
    if search:
        stmt = stmt.where(
            or_(
                Notice.title.ilike("%" + search + "%"),
                Notice.id.cast(String) == search,
            )
        )
    if status:
        stmt = stmt.where(Notice.verification_status == status)
    if office:
        stmt = stmt.where(Notice.publisher == office)
    return list_page(
        db,
        stmt.order_by(
            Notice.created_at.desc() if sort == "newest" else Notice.created_at,
            Notice.id,
        ),
        page,
        page_size,
        serialize,
    )


@router.get("/notices/{key}")
def notice_detail(key: uuid.UUID, db: Session = Depends(get_db)):
    item = db.scalar(select(Notice).where(Notice.id == key, *visible_notice()))
    if not item:
        raise HTTPException(404, "Record not found")
    return serialize(item)


@router.post("/admin/notices", status_code=201)
def add_notice(
    body: NoticeBody, db: Session = Depends(get_db), actor: User = Depends(admin_user)
):
    data = body.model_dump(exclude={"version"})
    data["source_url"] = str(body.source_url)
    item = Notice(**data, lifecycle="draft", created_by=actor.id, updated_by=actor.id)
    db.add(item)
    db.flush()
    audit(db, actor, item, "create")
    db.commit()
    return serialize(item)


@router.put("/admin/notices/{key}")
def edit_notice(
    key: uuid.UUID,
    body: NoticeBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = locked(db, Notice, key, body.version)
    audit(db, actor, item, "before_edit")
    for k, v in body.model_dump(exclude={"version"}).items():
        setattr(item, k, str(v) if k == "source_url" else v)
    item.lifecycle = "draft"
    item.verification_status = "unverified"
    item.verified_by = None
    item.verified_at = None
    item.version += 1
    item.updated_by = actor.id
    for schedule in db.scalars(
        select(Schedule)
        .where(Schedule.notice_id == item.id, Schedule.status == "announced")
        .with_for_update()
    ):
        audit(db, actor, schedule, "notice_revision")
        schedule.status = "superseded"
        schedule.version += 1
    # Material revisions require a new notice review before schedules can be public.
    db.commit()
    return serialize(item)


@router.post("/admin/notices/{key}/{action}")
def notice_action(
    key: uuid.UUID,
    action: Literal["verify", "publish", "withdraw", "archive"],
    body: VersionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = locked(db, Notice, key, body.version)
    db.info["audit_reason"] = body.reason
    if action in {"cancel", "withdraw", "archive"} and len(body.reason.strip()) < 5:
        raise HTTPException(422, "Reason of at least five characters required")
    audit(db, actor, item, action)
    if action == "verify":
        item.verification_status = "verified"
        item.verified_by = actor.id
        item.verified_at = now()
    elif action == "publish":
        if item.verification_status != "verified":
            raise HTTPException(422, "Admin verification required before publishing")
        item.lifecycle = "published"
    else:
        item.lifecycle = "withdrawn" if action == "withdraw" else "archived"
    item.version += 1
    item.updated_by = actor.id
    db.commit()
    return serialize(item)


@router.delete("/admin/notices/{key}", status_code=204)
def delete_notice(
    key: uuid.UUID,
    version: int,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = locked(db, Notice, key, version)
    if (
        item.lifecycle != "draft"
        or db.scalar(
            select(EvidenceAudit.id)
            .where(EvidenceAudit.entity_id == key, EvidenceAudit.action == "publish")
            .limit(1)
        )
        or db.scalar(select(Schedule.id).where(Schedule.notice_id == key).limit(1))
    ):
        raise HTTPException(
            409, "Preserve published/referenced evidence; withdraw or archive instead"
        )
    audit(db, actor, item, "delete")
    db.delete(item)
    db.commit()


def schedule_json(s):
    return serialize(s) | {
        "window_state": "upcoming"
        if now() < s.starts_at
        else "within_announced_window"
        if now() < s.ends_at
        else "announced_window_ended"
    }


def schedule_query():
    return (
        select(Schedule)
        .join(Notice, Notice.id == Schedule.notice_id)
        .where(
            *visible_notice(),
            Schedule.lifecycle == "published",
            Schedule.is_demo.is_(False),
        )
    )


@router.get("/schedules")
def schedule_list(
    db: Session = Depends(get_db),
    location_id: uuid.UUID | None = None,
    search: str = Query("", max_length=240),
    office: str | None = None,
    feeder: str | None = None,
    category: str | None = None,
    status: Literal["announced", "cancelled", "superseded"] | None = None,
    starts_before: datetime | None = None,
    ends_after: datetime | None = None,
    sort: Literal["newest", "oldest"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = schedule_query()
    if location_id:
        stmt = stmt.where(
            or_(
                Schedule.location_id == location_id,
                Schedule.coverage.contains([{"id": str(location_id)}]),
            )
        )
    if search:
        stmt = stmt.where(
            or_(
                Notice.title.ilike("%" + search + "%"),
                Schedule.id.cast(String) == search,
            )
        )
    if office:
        stmt = stmt.where(Notice.publisher == office)
    if feeder:
        stmt = stmt.where(
            False
        )  # Registry claims are not implicit schedule coverage; never infer mappings.
    if category:
        stmt = stmt.where(Schedule.category == category)
    if status:
        stmt = stmt.where(Schedule.status == status)
    if starts_before and starts_before.tzinfo is None:
        raise HTTPException(422, "Timezone offset required")
    if ends_after and ends_after.tzinfo is None:
        raise HTTPException(422, "Timezone offset required")
    if starts_before:
        stmt = stmt.where(Schedule.starts_at < aware(starts_before))
    if ends_after:
        stmt = stmt.where(Schedule.ends_at > aware(ends_after))
    result = list_page(
        db,
        stmt.order_by(
            Schedule.starts_at.desc() if sort == "newest" else Schedule.starts_at,
            Schedule.id,
        ),
        page,
        page_size,
        schedule_json,
    )

    # Bounded batch of public source metadata: never a lazy lookup per schedule.
    ids = {item["notice_id"] for item in result["items"]}
    sources = (
        {
            n.id: {
                k: getattr(n, k)
                for k in ("source_url", "publisher", "published_at", "updated_at")
            }
            for n in db.scalars(select(Notice).where(Notice.id.in_(ids)))
        }
        if ids
        else {}
    )
    for item in result["items"]:
        item["notice"] = sources.get(item["notice_id"])
    return result


@router.get("/schedules/{key}")
def schedule_detail(key: uuid.UUID, db: Session = Depends(get_db)):
    item = db.scalar(schedule_query().where(Schedule.id == key))
    if not item:
        raise HTTPException(404, "Record not found")
    return schedule_json(item)


def schedule_values(db, body):
    if body.feeder_id:
        raise HTTPException(
            422,
            "Schedule feeder integration is unavailable; use explicit source-named locations",
        )
    if body.ends_at <= body.starts_at:
        raise HTTPException(422, "End must follow start")
    notice = find(db, Notice, body.notice_id)
    if notice.verification_status != "verified":
        raise HTTPException(422, "Verified notice required")
    ids = list(dict.fromkeys([body.location_id] + body.location_ids))
    ancestor_rows = db.execute(
        text("""
        WITH RECURSIVE chain AS (
          SELECT id AS root,id,parent_id,ARRAY[id] AS path FROM locations WHERE id=ANY(:keys)
          UNION ALL
          SELECT c.root,p.id,p.parent_id,c.path || p.id FROM chain c
          JOIN locations p ON p.id=c.parent_id WHERE NOT p.id=ANY(c.path)
        ) SELECT root,id FROM chain WHERE root!=id
    """),
        {"keys": ids},
    ).all()
    ancestors = {key: [] for key in ids}
    for root, ancestor in ancestor_rows:
        ancestors[root].append(str(ancestor))
    coverage = []
    for key in ids:
        loc = find(db, Location, key)
        if loc.verification_status != "verified":
            raise HTTPException(422, "Verified locations required")
        coverage.append(
            {
                "id": str(loc.id),
                "name_bn": loc.name_bn,
                "kind": loc.kind,
                "ancestor_ids": ancestors[key],
            }
        )
    data = body.model_dump(exclude={"version", "location_ids", "feeder_id"})
    return data | {"coverage": coverage, "is_demo": notice.is_demo}


@router.post("/admin/schedules", status_code=201)
def add_schedule(
    body: ScheduleBody, db: Session = Depends(get_db), actor: User = Depends(admin_user)
):
    item = Schedule(
        **schedule_values(db, body),
        lifecycle="draft",
        created_by=actor.id,
        updated_by=actor.id,
    )
    db.add(item)
    db.flush()
    audit(db, actor, item, "create")
    db.commit()
    duplicate = db.scalar(
        select(Schedule.id)
        .where(
            Schedule.id != item.id,
            Schedule.location_id == item.location_id,
            Schedule.starts_at < item.ends_at,
            Schedule.ends_at > item.starts_at,
        )
        .limit(1)
    )
    return schedule_json(item) | {
        "warning": "Overlapping announcement; review possible duplicate"
        if duplicate
        else None
    }


@router.put("/admin/schedules/{key}")
def edit_schedule(
    key: uuid.UUID,
    body: ScheduleBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = locked(db, Schedule, key, body.version)
    audit(db, actor, item, "before_edit")
    for k, v in schedule_values(db, body).items():
        setattr(item, k, v)
    item.lifecycle = "draft"
    item.version += 1
    item.updated_by = actor.id
    db.commit()
    return schedule_json(item)


@router.post("/admin/schedules/{key}/{action}")
def schedule_action(
    key: uuid.UUID,
    action: Literal["publish", "cancel", "archive"],
    body: VersionBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = locked(db, Schedule, key, body.version)
    db.info["audit_reason"] = body.reason
    if action in {"cancel", "withdraw", "archive"} and len(body.reason.strip()) < 5:
        raise HTTPException(422, "Reason of at least five characters required")
    audit(db, actor, item, action)
    if action == "publish":
        n = find(db, Notice, item.notice_id)
        if n.lifecycle != "published" or n.verification_status != "verified":
            raise HTTPException(422, "Published verified notice required")
        item.lifecycle = "published"
        item.status = "announced"
    elif action == "cancel":
        item.status = "cancelled"
    else:
        item.lifecycle = "archived"
    item.version += 1
    item.updated_by = actor.id
    db.commit()
    return schedule_json(item)


@router.delete("/admin/schedules/{key}", status_code=204)
def delete_schedule(
    key: uuid.UUID,
    version: int,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = locked(db, Schedule, key, version)
    if item.lifecycle != "draft" or db.scalar(
        select(EvidenceAudit.id)
        .where(EvidenceAudit.entity_id == key, EvidenceAudit.action == "publish")
        .limit(1)
    ):
        raise HTTPException(
            409, "Cancel or archive previously published evidence instead"
        )
    audit(db, actor, item, "delete")
    db.delete(item)
    db.commit()


@router.get("/admin/evidence/{entity}/{key}/revisions")
def revisions(
    entity: Literal["notices", "schedules", "reports"],
    key: uuid.UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
):
    return {
        "items": [
            serialize(a)
            for a in db.scalars(
                select(EvidenceAudit)
                .where(
                    EvidenceAudit.entity_type == entity, EvidenceAudit.entity_id == key
                )
                .order_by(EvidenceAudit.created_at, EvidenceAudit.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ]
    }


class Observation(ReportInput):
    model_config = ConfigDict(extra="forbid")
    note: str = Field(default="", max_length=500)


@router.post("/reports", status_code=201)
def submit_report(
    body: Observation, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    # One database lock per reporter; independent people never share a dedup key.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    existing = db.scalar(
        select(Report).where(
            Report.user_id == user.id, Report.idempotency_key == body.idempotency_key
        )
    )
    if existing:
        if any(
            getattr(existing, k) != getattr(body, k)
            for k in ["location_id", "kind", "observed_at", "note"]
        ):
            raise HTTPException(409, "Idempotency key reused with different payload")
        return report_json(existing)
    loc = find(db, Location, body.location_id)
    if loc.verification_status != "verified":
        raise HTTPException(422, "Verified reporting location required")
    config = get_settings()
    instant = now()
    if (
        not instant - timedelta(hours=config.report_backdate_hours)
        <= body.observed_at
        <= instant + timedelta(seconds=config.report_future_seconds)
    ):
        raise HTTPException(422, "Observation outside allowed time window")
    count = db.scalar(
        select(func.count())
        .select_from(Report)
        .where(
            Report.user_id == user.id, Report.created_at > instant - timedelta(hours=1)
        )
    )
    if count >= config.report_rate_limit:
        raise HTTPException(429, "Hourly report limit reached")
    previous = db.scalar(
        select(Report)
        .where(
            Report.user_id == user.id,
            Report.location_id == loc.id,
            Report.moderation == "accepted",
        )
        .order_by(Report.observed_at.desc(), Report.id.desc())
        .limit(1)
    )
    if (
        previous
        and previous.kind == body.kind
        and previous.created_at
        > instant - timedelta(seconds=config.report_cooldown_seconds)
    ):
        raise HTTPException(
            429, "Identical observation cooldown; your existing evidence remains"
        )
    ep = db.scalar(
        select(PersonalEpisode)
        .where(
            PersonalEpisode.user_id == user.id,
            PersonalEpisode.location_id == loc.id,
            PersonalEpisode.is_open.is_(True),
        )
        .with_for_update()
    )
    item = Report(user_id=user.id, **body.model_dump(), moderation="accepted")
    if (
        ep
        and body.kind == "power_back"
        and ep.started_at
        and body.observed_at < ep.started_at
    ):
        raise HTTPException(422, "Restoration precedes personal outage start")
    if body.observed_at > instant or (
        previous and body.observed_at < previous.observed_at
    ):
        # A clock-skew-tolerated submission is retained, not treated as a future fact.
        item.moderation = "pending"
    else:
        # Consecutive restoration confirmations belong to the previous episode;
        # they do not invent a new interruption or move its first reported end.
        if (
            not ep
            and body.kind == "power_back"
            and previous
            and previous.kind == "power_back"
            and previous.episode_id
        ):
            ep = db.get(PersonalEpisode, previous.episode_id)
        if not ep:
            ep = PersonalEpisode(
                user_id=user.id,
                location_id=loc.id,
                started_at=body.observed_at if body.kind == "power_off" else None,
                last_observed_at=body.observed_at,
                is_open=body.kind != "power_back",
                ended_at=body.observed_at if body.kind == "power_back" else None,
            )
            db.add(ep)
            db.flush()
        else:
            ep.last_observed_at = body.observed_at
            if body.kind == "power_back" and ep.is_open:
                ep.ended_at = body.observed_at
                ep.is_open = False
        item.episode_id = ep.id
    db.add(item)
    db.commit()
    return report_json(item)


@router.get("/reports")
def recent_reports(
    location_id: uuid.UUID,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return list_page(
        db,
        select(Report)
        .where(
            Report.location_id == location_id,
            Report.moderation == "accepted",
            Report.is_demo.is_(False),
        )
        .order_by(Report.observed_at.desc(), Report.id),
        page,
        page_size,
        report_json,
    )


@router.get("/me/reports")
def own_reports(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return list_page(
        db,
        select(Report)
        .where(Report.user_id == user.id)
        .order_by(Report.created_at.desc(), Report.id),
        page,
        page_size,
        serialize,
    )


@router.get("/me/episodes")
def own_episodes(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return list_page(
        db,
        select(PersonalEpisode)
        .where(PersonalEpisode.user_id == user.id)
        .order_by(PersonalEpisode.last_observed_at.desc(), PersonalEpisode.id),
        page,
        page_size,
        lambda e: (
            serialize(e)
            | {
                "duration_seconds": (e.ended_at - e.started_at).total_seconds()
                if e.started_at and e.ended_at
                else None
            }
        ),
    )


@router.get("/reports/summary")
def summary(location_id: uuid.UUID, db: Session = Depends(get_db)):
    instant = now()
    start = instant - timedelta(minutes=get_settings().community_window_minutes)
    latest = (
        select(
            Report.kind,
            Report.observed_at,
            func.row_number()
            .over(
                partition_by=Report.user_id,
                order_by=(
                    Report.observed_at.desc(),
                    Report.created_at.desc(),
                    Report.id.desc(),
                ),
            )
            .label("rank"),
        )
        .where(
            Report.location_id == location_id,
            Report.observed_at >= start,
            Report.observed_at <= instant,
            Report.moderation == "accepted",
            Report.is_demo.is_(False),
        )
        .subquery()
    )
    counts = dict.fromkeys(["power_off", "power_back", "still_off"], 0)
    latest_time = None
    for kind, count, observed in db.execute(
        select(latest.c.kind, func.count(), func.max(latest.c.observed_at))
        .where(latest.c.rank == 1)
        .group_by(latest.c.kind)
    ):
        counts[kind] = count
        latest_time = max(latest_time, observed) if latest_time else observed
    off = counts["power_off"] + counts["still_off"]
    label = (
        "mixed"
        if off and counts["power_back"]
        else "interruptions_reported"
        if off
        else "restoration_reports"
        if counts["power_back"]
        else "no_recent_reports"
    )
    return {
        "counts": counts,
        "unique_reporters": sum(counts.values()),
        "evidence_label": label,
        "window_start": start,
        "window_end": instant,
        "retrieved_at": instant,
        "latest_observed_at": latest_time,
        "scope": "individual_connections_only",
        "area_status": "unknown",
    }


class ModerationBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(default=1, ge=1)
    state: Literal["accepted", "rejected", "pending"]
    reason: str = Field(min_length=5, max_length=500)
    candidate_event_id: uuid.UUID | None = None


@router.post("/admin/reports/{key}/moderate")
def moderate(
    key: uuid.UUID,
    body: ModerationBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = find(db, Report, key)
    db.scalar(select(User).where(User.id == item.user_id).with_for_update())
    db.refresh(item)
    if item.version != body.version:
        raise HTTPException(409, "Report changed; reload before reviewing")
    if body.state == "accepted" and item.observed_at > now():
        raise HTTPException(
            422, "Future observations require review after their observation time"
        )
    item.version += 1
    db.info["audit_reason"] = body.reason
    if body.candidate_event_id:
        event = find(db, OutageEvent, body.candidate_event_id)
        if event.location_id != item.location_id:
            raise HTTPException(422, "Event scope differs")
    db.add(
        EvidenceAudit(
            actor_id=actor.id,
            entity_id=item.id,
            entity_type="reports",
            action="moderate",
            snapshot=jsonable_encoder(serialize(item))
            | {"reason": body.reason, "new_state": body.state},
        )
    )
    item.moderation = body.state
    item.candidate_event_id = body.candidate_event_id
    db.flush()
    rebuild_episodes(db, item.user_id, item.location_id)
    db.commit()
    return report_json(item)


@router.get("/admin/notices")
def admin_notice_list(
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=240),
):
    return list_page(
        db,
        select(Notice)
        .where(Notice.title.ilike("%" + search + "%"))
        .order_by(Notice.created_at.desc(), Notice.id),
        page,
        page_size,
        serialize,
    )


@router.get("/admin/schedules")
def admin_schedule_list(
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return list_page(
        db,
        select(Schedule).order_by(Schedule.created_at.desc(), Schedule.id),
        page,
        page_size,
        schedule_json,
    )


def rebuild_episodes(db, user_id, location_id):
    """Review corrections rebuild only personal history from remaining accepted evidence."""
    rows = db.scalars(
        select(Report)
        .where(Report.user_id == user_id, Report.location_id == location_id)
        .order_by(Report.observed_at, Report.created_at, Report.id)
    ).all()
    for r in rows:
        r.episode_id = None
    db.flush()
    for ep in db.scalars(
        select(PersonalEpisode).where(
            PersonalEpisode.user_id == user_id,
            PersonalEpisode.location_id == location_id,
        )
    ):
        db.delete(ep)
    db.flush()
    ep = None
    last_closed = None
    for r in rows:
        if r.moderation != "accepted" or r.is_demo or r.observed_at > now():
            continue
        if ep is None and r.kind == "power_back" and last_closed is not None:
            r.episode_id = last_closed.id
            last_closed.last_observed_at = r.observed_at
            continue
        if ep is None:
            ep = PersonalEpisode(
                user_id=user_id,
                location_id=location_id,
                started_at=r.observed_at if r.kind == "power_off" else None,
                last_observed_at=r.observed_at,
                is_open=True,
            )
            db.add(ep)
            db.flush()
        r.episode_id = ep.id
        ep.last_observed_at = r.observed_at
        if r.kind == "power_back":
            ep.ended_at = r.observed_at
            ep.is_open = False
            last_closed = ep
            ep = None


@router.get("/admin/reports")
def admin_reports(
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return list_page(
        db,
        select(Report).order_by(Report.created_at.desc(), Report.id),
        page,
        page_size,
        serialize,
    )
