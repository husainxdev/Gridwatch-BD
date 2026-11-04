"""Public area evidence and private dashboard snapshots; plans never imply power state."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from .api import find, loc_json
from .config import get_settings
from .data_mode import evidence_visibility
from .db import get_db
from .evidence import report_json, schedule_json, serialize, summary, visible_notice
from .models import Location, Notice, PersonalEpisode, Report, Schedule, User
from .security import current_user, now

router = APIRouter(prefix="/api", tags=["user dashboard"])


def build_area_overview(db, location_id, page):
    area = find(db, Location, location_id)
    instant = now()
    dhaka = timezone(timedelta(hours=6))
    day_start = datetime.combine(
        instant.astimezone(dhaka).date(), datetime.min.time(), tzinfo=dhaka
    )
    horizon = day_start + timedelta(days=8)
    statement = (
        select(Schedule, Notice)
        .join(Notice, Notice.id == Schedule.notice_id)
        .where(
            *visible_notice(),
            Schedule.lifecycle == "published",
            evidence_visibility(Schedule),
            or_(
                Schedule.location_id == location_id,
                Schedule.coverage.contains([{"id": str(location_id)}]),
                Schedule.coverage.contains([{"ancestor_ids": [str(location_id)]}]),
            ),
            Schedule.ends_at > day_start,
            Schedule.starts_at < horizon,
        )
    )
    total = db.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    rows = db.execute(
        statement.order_by(Schedule.starts_at, Schedule.id)
        .offset((page - 1) * 10)
        .limit(10)
    ).all()
    schedules = [
        {
            k: v
            for k, v in schedule_json(s).items()
            if k not in {"created_by", "updated_by"}
        }
        | {
            "partial_coverage": s.location_id != location_id
            and not any(x.get("id") == str(location_id) for x in s.coverage),
            "notice": {
                "id": n.id,
                "title": n.title,
                "publisher": n.publisher,
                "source_url": n.source_url,
                "published_at": n.published_at,
                "updated_at": n.updated_at,
                "verification_status": n.verification_status,
                "verified_at": n.verified_at,
            },
        }
        for s, n in rows
    ]
    ancestors = (
        db.execute(
            text("""
        WITH RECURSIVE ancestors AS (
          SELECT id,parent_id,name_bn,0 AS depth,ARRAY[id] AS path FROM locations WHERE id=:key
          UNION ALL
          SELECT p.id,p.parent_id,p.name_bn,a.depth+1,a.path || p.id
          FROM locations p JOIN ancestors a ON p.id=a.parent_id
          WHERE NOT p.id=ANY(a.path)
        ) SELECT id,name_bn FROM ancestors ORDER BY depth DESC
    """),
            {"key": location_id},
        )
        .mappings()
        .all()
    )
    community = summary(location_id, db)
    observations = db.scalars(
        select(Report)
        .where(
            Report.location_id == location_id,
            Report.moderation == "accepted",
            evidence_visibility(Report),
            Report.observed_at <= instant,
        )
        .order_by(Report.observed_at.desc(), Report.created_at.desc(), Report.id.desc())
        .limit(5)
    ).all()
    return {
        "area": loc_json(area),
        "available": area.verification_status == "verified",
        "breadcrumb": [dict(a) for a in ancestors],
        "retrieved_at": instant,
        "schedules": {
            "items": schedules,
            "total": total,
            "page": page,
            "page_size": 10,
            "from": day_start,
            "until": horizon,
        },
        "community": community,
        "instance_mode": "demo" if get_settings().demo_instance else "pilot",
        "recent_reports": [
            {
                k: v
                for k, v in report_json(r).items()
                if k
                in {
                    "id",
                    "kind",
                    "location_id",
                    "observed_at",
                    "created_at",
                    "scope",
                    "is_demo",
                }
            }
            for r in observations
        ],
        "restoration_estimate": None,
    }


def build_dashboard(db, user_id, location_id, page):
    common = build_area_overview(db, location_id, page)
    instant = common["retrieved_at"]
    latest = db.scalar(
        select(Report)
        .where(
            Report.user_id == user_id,
            Report.location_id == location_id,
            Report.moderation == "accepted",
            evidence_visibility(Report),
            Report.observed_at <= instant,
        )
        .order_by(Report.observed_at.desc(), Report.created_at.desc(), Report.id.desc())
        .limit(1)
    )
    episode = db.scalar(
        select(PersonalEpisode)
        .where(
            PersonalEpisode.user_id == user_id,
            PersonalEpisode.location_id == location_id,
        )
        .order_by(
            PersonalEpisode.is_open.desc(),
            PersonalEpisode.last_observed_at.desc(),
            PersonalEpisode.id.desc(),
        )
        .limit(1)
    )
    recent = db.scalars(
        select(Report)
        .where(Report.user_id == user_id, Report.location_id == location_id)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .limit(5)
    ).all()
    history = db.scalars(
        select(PersonalEpisode)
        .where(
            PersonalEpisode.user_id == user_id,
            PersonalEpisode.location_id == location_id,
        )
        .order_by(PersonalEpisode.last_observed_at.desc(), PersonalEpisode.id.desc())
        .limit(5)
    ).all()
    return common | {
        "personal": {
            "latest_report": serialize(latest) if latest else None,
            "episode": serialize(episode) if episode else None,
            "recent": [serialize(r) for r in recent],
            "history": [serialize(e) for e in history],
        }
    }


@router.get("/dashboard")
def dashboard(
    location_id: uuid.UUID,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    # Authentication only reads. Release its lease before acquiring the snapshot,
    # so a small pool does not need two simultaneous connections per request.
    user_id = user.id
    db.rollback()
    # A consistent snapshot across the small fixed query set, after authentication.
    with (
        db.get_bind()
        .connect()
        .execution_options(isolation_level="REPEATABLE READ") as connection
    ):
        with Session(bind=connection) as snapshot:
            return build_dashboard(snapshot, user_id, location_id, page)


@router.get("/area-overview")
def area_overview(
    location_id: uuid.UUID,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    # Public output is constructed separately: no user, session, note or history fields.
    with (
        db.get_bind()
        .connect()
        .execution_options(isolation_level="REPEATABLE READ") as connection
    ):
        with Session(bind=connection) as snapshot:
            return build_area_overview(snapshot, location_id, page)
