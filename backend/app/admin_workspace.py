"""Bounded management lists; authorization is independent of the client workspace."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from .api import aware, find, list_page
from .data_mode import evidence_visibility
from .db import get_db
from .evidence import serialize, visible_notice
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
from .security import admin_user, now

router = APIRouter(prefix="/api/admin", tags=["admin workspace"])
MODELS = {
    "notices": Notice,
    "schedules": Schedule,
    "reports": Report,
    "locations": Location,
    "events": OutageEvent,
    "audit": EvidenceAudit,
}


@router.get("/overview")
def overview(db: Session = Depends(get_db), actor: User = Depends(admin_user)):
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where))

    return {
        "draft_notices": count(
            Notice, Notice.lifecycle == "draft", evidence_visibility(Notice)
        ),
        "upcoming_schedules": db.scalar(
            select(func.count())
            .select_from(Schedule)
            .join(Notice)
            .where(
                *visible_notice(),
                Schedule.lifecycle == "published",
                Schedule.status == "announced",
                evidence_visibility(Schedule),
                Schedule.starts_at >= now(),
            )
        ),
        "pending_reports": count(
            Report, Report.moderation == "pending", evidence_visibility(Report)
        ),
        "unrestored_events": count(OutageEvent, OutageEvent.restored_at.is_(None)),
        "candidate_events_supported": False,
        "at": now(),
    }


@router.get("/list/{entity}")
def listing(
    entity: Literal["notices", "schedules", "reports", "locations", "events", "audit"],
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
    search: str = Query("", max_length=240),
    status: str = Query("", max_length=30),
    location_id: uuid.UUID | None = None,
    office: str = Query("", max_length=160),
    category: str = Query("", max_length=100),
    kind: str = Query("", max_length=32),
    start: datetime | None = None,
    end: datetime | None = None,
    sort: Literal["newest", "oldest", "name", "time"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    m = MODELS[entity]
    stmt = select(m)
    if entity in {"notices", "schedules", "reports"}:
        stmt = stmt.where(evidence_visibility(m))
    names = {
        "notices": Notice.title,
        "locations": Location.name_bn,
        "schedules": Schedule.category,
        "reports": Report.kind,
        "events": OutageEvent.start_evidence,
        "audit": EvidenceAudit.action,
    }
    time = {
        "schedules": Schedule.starts_at,
        "reports": Report.observed_at,
        "events": OutageEvent.started_at,
    }.get(entity, m.created_at)
    if search:
        cond = [names[entity].ilike("%" + search + "%"), cast(m.id, String) == search]
        if entity == "locations":
            cond += [
                Location.name_en.ilike("%" + search + "%"),
                cast(Location.aliases, String).ilike("%" + search + "%"),
            ]
        if entity == "audit":
            cond += [cast(EvidenceAudit.entity_id, String) == search]
        if entity == "schedules":
            cond += [
                Schedule.notice_id.in_(
                    select(Notice.id).where(Notice.title.ilike("%" + search + "%"))
                )
            ]
        stmt = stmt.where(or_(*cond))
    if status:
        allowed = {
            "notices": {"draft", "published", "withdrawn", "archived"},
            "schedules": {"draft", "published", "archived", "cancelled", "superseded"},
            "reports": {"pending", "accepted", "rejected"},
            "locations": {"verified", "unverified"},
            "events": {"open", "completed"},
            "audit": set(),
        }
        if status not in allowed[entity]:
            raise HTTPException(422, "Invalid status for entity")
        if entity == "events":
            stmt = stmt.where(
                OutageEvent.restored_at.is_(None)
                if status == "open"
                else OutageEvent.restored_at.is_not(None)
            )
        else:
            column = (
                m.status
                if entity == "schedules" and status in {"cancelled", "superseded"}
                else m.lifecycle
                if entity in {"notices", "schedules"}
                else m.moderation
                if entity == "reports"
                else m.verification_status
            )
            stmt = stmt.where(column == status)
            if entity == "schedules" and status == "published":
                stmt = stmt.where(
                    Schedule.status == "announced",
                    Schedule.notice_id.in_(select(Notice.id).where(*visible_notice())),
                )
    if location_id:
        if entity in {"schedules", "notices"}:
            covered = or_(
                Schedule.location_id == location_id,
                Schedule.coverage.contains([{"id": str(location_id)}]),
            )
            stmt = stmt.where(
                covered
                if entity == "schedules"
                else Notice.id.in_(select(Schedule.notice_id).where(covered))
            )
        elif entity in {"reports", "events"}:
            stmt = stmt.where(m.location_id == location_id)
        elif entity == "locations":
            stmt = stmt.where(Location.parent_id == location_id)
        else:
            raise HTTPException(422, "Location filter unavailable")
    if office:
        if entity == "notices":
            stmt = stmt.where(Notice.publisher == office)
        elif entity == "schedules":
            stmt = stmt.where(
                Schedule.notice_id.in_(
                    select(Notice.id).where(Notice.publisher == office)
                )
            )
        else:
            raise HTTPException(422, "Office filter unavailable")
    if category:
        if entity == "schedules":
            stmt = stmt.where(Schedule.category == category)
        elif entity == "notices":
            stmt = stmt.where(
                Notice.id.in_(
                    select(Schedule.notice_id).where(Schedule.category == category)
                )
            )
        else:
            raise HTTPException(422, "Category filter unavailable")
    if kind:
        if entity not in {"locations", "reports"}:
            raise HTTPException(422, "Type filter unavailable")
        stmt = stmt.where(m.kind == kind)
    if start:
        if start.tzinfo is None:
            raise HTTPException(422, "Timezone offset required")
        aware(start)
        stmt = stmt.where(time >= start)
    if end:
        if end.tzinfo is None:
            raise HTTPException(422, "Timezone offset required")
        aware(end)
        stmt = stmt.where(time < end)
    if start and end and end <= start:
        raise HTTPException(422, "End must follow start")
    order = {
        "newest": m.created_at.desc(),
        "oldest": m.created_at,
        "name": names[entity],
        "time": time,
    }[sort]
    result = list_page(db, stmt.order_by(order, m.id), page, page_size, serialize)
    # One joined lookup for all visible location names, never N+1.
    ids = {r["location_id"] for r in result["items"] if "location_id" in r}
    labels = (
        dict(
            db.execute(
                select(Location.id, Location.name_bn).where(Location.id.in_(ids))
            ).all()
        )
        if ids
        else {}
    )
    for r in result["items"]:
        if "location_id" in r:
            r["location_name"] = labels.get(r["location_id"])
        r.pop("idempotency_key", None)
    return result


@router.get("/reports/{key}/context")
def report_context(
    key: uuid.UUID, db: Session = Depends(get_db), actor: User = Depends(admin_user)
):
    report = find(db, Report, key)
    episode = db.get(PersonalEpisode, report.episode_id) if report.episode_id else None
    schedules = db.execute(
        select(Schedule, Notice)
        .join(Notice)
        .where(
            or_(
                Schedule.location_id == report.location_id,
                Schedule.coverage.contains([{"id": str(report.location_id)}]),
            ),
            Schedule.starts_at <= report.observed_at,
            Schedule.ends_at > report.observed_at,
            evidence_visibility(Schedule),
            evidence_visibility(Notice),
        )
        .order_by(Schedule.starts_at, Schedule.id)
        .limit(20)
    ).all()
    return {
        "episode": serialize(episode) if episode else None,
        "schedules": [
            {
                "id": s.id,
                "title": n.title,
                "source_url": n.source_url,
                "status": s.status,
                "lifecycle": s.lifecycle,
            }
            for s, n in schedules
        ],
        "schedule_limit": 20,
        "note": "Time and named-area match only; not proof of cause",
    }


@router.get("/offices")
def offices(
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
    search: str = Query("", max_length=160),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    stmt = (
        select(Notice.publisher, func.count().label("notices"))
        .where(evidence_visibility(Notice), Notice.publisher.ilike("%" + search + "%"))
        .group_by(Notice.publisher)
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    return {
        "items": [
            dict(r)
            for r in db.execute(
                stmt.order_by(Notice.publisher)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).mappings()
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "registry_status": "Notice publisher metadata only; source-reviewed offices and mappings are managed separately under /admin/registry",
    }
