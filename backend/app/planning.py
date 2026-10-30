"""Private activities and recorded personal history. All intervals are half open."""

import uuid
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ConfigDict, Field, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .api import ActivityInput, aware, find, list_page
from .config import get_settings
from .data_mode import evidence_visibility
from .db import get_db
from .evidence import serialize, visible_notice
from .models import (
    Activity,
    EvidenceAudit,
    Location,
    Notice,
    PersonalEpisode,
    Report,
    Schedule,
    User,
)
from .security import current_user, now

router = APIRouter(prefix="/api", tags=["activities and personal history"])
DHAKA = ZoneInfo("Asia/Dhaka")


def interval(start, end, maximum=366):
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(422, "Timezone offset required")
    aware(start)
    aware(end)
    if end <= start or end - start > timedelta(days=maximum):
        raise HTTPException(
            422, f"Positive interval of at most {maximum} days required"
        )


def union_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if end < start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def minutes(intervals):
    return sum((b - a).total_seconds() / 60 for a, b in union_intervals(intervals))


def check_activity(db, location_id, start, end):
    interval(start, end, 7)
    location = find(db, Location, location_id)
    if location.verification_status != "verified":
        raise HTTPException(
            422, "Location is unavailable; coverage cannot be confirmed"
        )
    # Snapshot ancestry is evidence at publication time, never an inferred feeder.
    ancestors = []
    ancestry_changed_at = location.updated_at
    cursor = location
    while cursor.parent_id and cursor.parent_id not in ancestors:
        ancestors.append(cursor.parent_id)
        cursor = find(db, Location, cursor.parent_id)
        ancestry_changed_at = max(ancestry_changed_at, cursor.updated_at)
    conditions = [
        Schedule.location_id == location_id,
        Schedule.coverage.contains([{"id": str(location_id)}]),
        Schedule.coverage.contains([{"ancestor_ids": [str(location_id)]}]),
    ]
    # A parent named without an explicit whole-area claim is uncertain coverage.
    for key in ancestors:
        conditions.append(Schedule.coverage.contains([{"id": str(key)}]))
    rows = db.execute(
        select(Schedule, Notice)
        .join(Notice)
        .where(
            *visible_notice(),
            Schedule.lifecycle == "published",
            Schedule.status == "announced",
            evidence_visibility(Schedule),
            Schedule.starts_at < end,
            Schedule.ends_at > start,
            or_(*conditions),
        )
        .order_by(Schedule.starts_at, Schedule.id)
        .limit(501)
    ).all()
    if len(rows) > 500:
        raise HTTPException(422, "Too many announcements; narrow the activity interval")
    conflicts, uncertain, ranges = [], [], []
    for s, n in rows:
        exact = s.location_id == location_id or any(
            x.get("id") == str(location_id) for x in s.coverage
        )
        whole_parent = (
            s.coverage_scope == "entire_administrative_area"
            and ancestry_changed_at <= s.created_at
            and any(x.get("id") in {str(a) for a in ancestors} for x in s.coverage)
        )
        a, b = max(start, s.starts_at), min(end, s.ends_at)
        data = {
            "id": s.id,
            "version": s.version,
            "starts_at": s.starts_at,
            "ends_at": s.ends_at,
            "affected_start": a,
            "affected_end": b,
            "affected_minutes": (b - a).total_seconds() / 60,
            "coverage": s.coverage,
            "coverage_scope": s.coverage_scope,
            "coverage_confirmed": exact or whole_parent,
            "updated_at": s.updated_at,
            "notice": {
                k: getattr(n, k)
                for k in (
                    "id",
                    "title",
                    "source_url",
                    "publisher",
                    "published_at",
                    "updated_at",
                    "verified_at",
                )
            },
        }
        if exact or whole_parent:
            conflicts.append(data)
            ranges.append((a, b))
        else:
            uncertain.append(data)
    return {
        "conflicts": conflicts,
        "uncertain": uncertain,
        "announced_overlap": bool(conflicts),
        "affected_minutes": minutes(ranges),
        "checked_at": now(),
        "message": "Your activity overlaps an announced interruption."
        if conflicts
        else "Coverage could not be confirmed."
        if uncertain
        else "No matching published interruption was found.",
        "disclaimer": "Announcements are plans; electricity availability is not guaranteed.",
    }


class ActivityBody(ActivityInput):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def valid(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Activity title required")
        interval(self.starts_at, self.ends_at, 7)
        return self


@router.post("/activities/check")
def check(
    body: ActivityInput,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return check_activity(db, body.location_id, body.starts_at, body.ends_at)


def owned(db, key, user, lock=False):
    stmt = select(Activity).where(Activity.id == key, Activity.user_id == user.id)
    item = db.scalar(stmt.with_for_update() if lock else stmt)
    if not item:
        raise HTTPException(404, "Activity not found")
    return item


@router.get("/activities")
def activities(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", max_length=160),
    location_id: uuid.UUID | None = None,
    sort: Literal["newest", "oldest", "start"] = "newest",
):
    stmt = select(Activity).where(
        Activity.user_id == user.id, Activity.title.ilike("%" + search + "%")
    )
    if location_id:
        stmt = stmt.where(Activity.location_id == location_id)
    order = {
        "newest": Activity.created_at.desc(),
        "oldest": Activity.created_at,
        "start": Activity.starts_at,
    }[sort]
    return list_page(db, stmt.order_by(order, Activity.id), page, page_size, serialize)


@router.post("/activities", status_code=201)
def save_activity(
    body: ActivityBody,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    check_activity(db, body.location_id, body.starts_at, body.ends_at)
    item = Activity(**body.model_dump(exclude={"version"}), user_id=user.id)
    db.add(item)
    db.commit()
    return serialize(item)


@router.get("/activities/{key}")
def activity(
    key: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    item = owned(db, key, user)
    return serialize(item) | {
        "check": check_activity(db, item.location_id, item.starts_at, item.ends_at)
    }


@router.put("/activities/{key}")
def edit_activity(
    key: uuid.UUID,
    body: ActivityBody,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = owned(db, key, user, True)
    if body.version != item.version:
        raise HTTPException(409, "Activity changed; reload before editing")
    check_activity(db, body.location_id, body.starts_at, body.ends_at)
    for k, v in body.model_dump(exclude={"version"}).items():
        setattr(item, k, v)
    item.version += 1
    db.commit()
    return serialize(item)


@router.delete("/activities/{key}", status_code=204)
def delete_activity(
    key: uuid.UUID,
    version: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = owned(db, key, user, True)
    if version != item.version:
        raise HTTPException(409, "Activity changed; reload before deleting")
    db.delete(item)
    db.commit()


def history_calculations(episodes, start, end):
    """One person's one-location scope. Incomplete bounds never invent downtime."""
    completed, clipped = [], []
    opened = incomplete = contradictory = starting = 0
    for e in episodes:
        a, b = e.started_at, e.ended_at
        if a and start <= a < end:
            starting += 1
        if a and b and b < a:
            contradictory += 1
        elif e.is_open:
            opened += 1
        elif a is None or b is None:
            incomplete += 1
        else:
            completed.append((a, b))
            if max(a, start) < min(b, end):
                clipped.append((max(a, start), min(b, end)))
    merged = union_intervals(clipped)
    daily = {}
    for a, b in merged:
        cursor = a.astimezone(DHAKA)
        while cursor < b:
            midnight = datetime.combine(
                cursor.date() + timedelta(days=1), datetime.min.time(), tzinfo=DHAKA
            )
            stop = min(b, midnight)
            day = cursor.date().isoformat()
            daily[day] = daily.get(day, 0) + (stop - cursor).total_seconds() / 60
            cursor = stop.astimezone(DHAKA)
    raw = sum((b - a).total_seconds() / 60 for a, b in clipped)
    overlap = raw > minutes(clipped) + 0.00001
    return {
        "recorded_episodes": len(episodes),
        "starting_in_range": starting,
        "completed": len(completed),
        "open": opened,
        "incomplete": incomplete,
        "contradictory": contradictory,
        "overlapping_records": overlap,
        "known_minutes": minutes(clipped),
        "average_completed_minutes": None
        if not completed or overlap or contradictory
        else sum((b - a).total_seconds() / 60 for a, b in completed) / len(completed),
        "daily": [{"date": k, "known_minutes": v} for k, v in sorted(daily.items())],
    }


def history_snapshot(
    location_id: uuid.UUID,
    start: datetime,
    end: datetime,
    status: Literal["all", "open", "completed", "incomplete"] = "all",
    sort: Literal["newest", "oldest"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    interval(start, end)
    find(db, Location, location_id)
    # Unknown start: last observed is the only defensible lower bound.
    lower = func.coalesce(PersonalEpisode.started_at, PersonalEpisode.last_observed_at)
    upper = func.coalesce(PersonalEpisode.ended_at, now())
    stmt = select(PersonalEpisode).where(
        PersonalEpisode.user_id == user.id,
        PersonalEpisode.location_id == location_id,
        lower < end,
        upper > start,
    )
    if status == "open":
        stmt = stmt.where(PersonalEpisode.is_open.is_(True))
    elif status == "completed":
        stmt = stmt.where(
            PersonalEpisode.is_open.is_(False),
            PersonalEpisode.started_at.is_not(None),
            PersonalEpisode.ended_at.is_not(None),
        )
    elif status == "incomplete":
        stmt = stmt.where(
            PersonalEpisode.is_open.is_(False),
            or_(
                PersonalEpisode.started_at.is_(None), PersonalEpisode.ended_at.is_(None)
            ),
        )
    # Bounded server calculation: refuse rather than truncate unusually dense histories.
    episodes = db.scalars(stmt.order_by(PersonalEpisode.id).limit(10001)).all()
    if len(episodes) > 10000:
        raise HTTPException(422, "History too large; narrow date range")
    summary = history_calculations(episodes, start, end)
    order = (
        PersonalEpisode.last_observed_at.desc()
        if sort == "newest"
        else PersonalEpisode.last_observed_at
    )
    result = list_page(
        db, stmt.order_by(order, PersonalEpisode.id), page, page_size, serialize
    )
    ids = [x["id"] for x in result["items"]]
    report_counts = dict(
        db.execute(
            select(Report.episode_id, func.count())
            .where(
                Report.episode_id.in_(ids),
                Report.user_id == user.id,
                Report.moderation == "accepted",
                evidence_visibility(Report),
            )
            .group_by(Report.episode_id)
        ).all()
    )
    reviewed = dict(
        db.execute(
            select(Report.episode_id, func.count(func.distinct(Report.id)))
            .join(EvidenceAudit, EvidenceAudit.entity_id == Report.id)
            .where(
                Report.episode_id.in_(ids),
                Report.user_id == user.id,
                EvidenceAudit.entity_type == "reports",
                EvidenceAudit.action == "moderate",
            )
            .group_by(Report.episode_id)
        ).all()
    )
    for e in result["items"]:
        e["reviewed_observations"] = reviewed.get(e["id"], 0)
        e["accepted_observations"] = report_counts.get(e["id"], 0)
        e["duration_minutes"] = (
            (e["ended_at"] - e["started_at"]).total_seconds() / 60
            if e["started_at"] and e["ended_at"] and not e["is_open"]
            else None
        )
    return result | {
        "summary": summary,
        "start": start,
        "end": end,
        "source": "fictional demo observations; not real electricity evidence"
        if get_settings().demo_instance
        else "accepted personal observations; pending/rejected/demo excluded",
        "scope": "one user, one selected location; incomplete monitoring",
        "checked_at": now(),
    }


@router.get("/history")
def history(
    location_id: uuid.UUID,
    start: datetime,
    end: datetime,
    status: Literal["all", "open", "completed", "incomplete"] = "all",
    sort: Literal["newest", "oldest"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    with (
        db.get_bind()
        .connect()
        .execution_options(isolation_level="REPEATABLE READ") as connection
    ):
        with Session(bind=connection) as snapshot:
            return history_snapshot(
                location_id=location_id,
                start=start,
                end=end,
                status=status,
                sort=sort,
                page=page,
                page_size=page_size,
                db=snapshot,
                user=user,
            )
