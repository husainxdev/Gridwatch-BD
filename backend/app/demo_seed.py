"""Populated fictional walkthrough, only in an empty isolated demo database.

This is not official data ingestion. Review statuses simulate the workflow; every
record is fictional and the instance must display the persistent demo warning.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from .config import get_settings
from .db import SessionLocal
from .demo_operator import require_demo_database
from .models import (
    Activity,
    EvidenceAudit,
    Location,
    Notice,
    OutageEvent,
    PersonalEpisode,
    Report,
    SavedArea,
    Schedule,
    User,
)
from .security import hash_password

DATASET = "gridwatch-fictional-walkthrough-v1"
SOURCE = "https://example.com/#gridwatch-fictional-demo-not-an-official-source"
DISCLAIMER = "কাল্পনিক ডেমো — বাস্তব বিদ্যুৎ তথ্য বা সরকারি যাচাই নয়।"


def key(name):
    return uuid.uuid5(uuid.NAMESPACE_URL, DATASET + ":" + name)


def seed_content(settings, db, instant=None):
    require_demo_database(settings)
    if (
        db.scalar(text("SELECT current_database()"))
        != make_url(settings.database_url).database
    ):
        raise ValueError("Connected database differs from the isolated demo target")
    db.execute(text("SELECT pg_advisory_xact_lock(34132)"))
    marker = db.get(EvidenceAudit, key("manifest"))
    if marker:
        return marker.snapshot | {"already_seeded": True}
    if any(
        db.scalar(select(func.count()).select_from(model))
        for model in (
            Location,
            Notice,
            Schedule,
            Report,
            PersonalEpisode,
            Activity,
            OutageEvent,
            SavedArea,
        )
    ):
        raise ValueError(
            "Demo walkthrough requires empty operational tables; existing data is preserved"
        )
    accounts = {account.email: account for account in db.scalars(select(User))}
    admin = accounts.get("gridwatch-demo-admin@example.com")
    user = accounts.get("gridwatch-demo-user@example.com")
    if (
        len(accounts) != 2
        or not admin
        or not user
        or admin.role != "admin"
        or user.role != "user"
    ):
        raise ValueError("Provision the private demo Admin/User pair first")
    instant = instant or datetime.now(UTC)
    if instant.tzinfo is None:
        raise ValueError("Timezone-aware fixture anchor required")
    instant = instant.astimezone(UTC).replace(microsecond=0)

    def audit(item, action="demo_fixture_created"):
        db.add(
            EvidenceAudit(
                id=key("audit:" + str(item.id)),
                actor_id=admin.id,
                entity_id=item.id,
                entity_type=item.__tablename__,
                action=action,
                snapshot={
                    "is_demo": True,
                    "disclaimer": DISCLAIMER,
                    "dataset": DATASET,
                },
            )
        )

    hierarchy = [
        ("division", "division", None, "বিভাগ"),
        ("district", "district", "division", "জেলা"),
        ("city", "city_corporation", "district", "সিটি কর্পোরেশন"),
        ("ward", "ward", "city", "ওয়ার্ড"),
        ("area-a", "neighborhood", "ward", "মহল্লা ক"),
        ("area-b", "neighborhood", "ward", "মহল্লা খ"),
        ("upazila", "upazila", "district", "উপজেলা"),
        ("union", "union", "upazila", "ইউনিয়ন"),
        ("village", "village", "union", "গ্রাম"),
    ]
    locations = {}
    for name, kind, parent, label in hierarchy:
        area = Location(
            id=key(name),
            name_bn="কাল্পনিক ডেমো " + label,
            name_en="Fictional demo " + name,
            slug="fictional-demo-" + name,
            kind=kind,
            parent_id=key(parent) if parent else None,
            aliases=["Demo A"]
            if name == "area-a"
            else ["Demo B"]
            if name == "area-b"
            else [],
            verification_status="verified",
            source_url=SOURCE,
            verified_at=instant,
        )
        db.add(area)
        db.flush()  # Parent FK ordering is explicit, including urban/rural branches.
        locations[name] = area
        audit(area, "demo_simulated_location_review")
    area = locations["area-a"]
    alternate = locations["area-b"]
    for account in (admin, user):
        db.add(
            SavedArea(
                user_id=account.id,
                location_id=area.id,
                is_default=True,
                label="কাল্পনিক ডেমো: নিজের সংযোগ",
            )
        )
        db.add(
            SavedArea(
                user_id=account.id,
                location_id=alternate.id,
                label="কাল্পনিক ডেমো: বিকল্প এলাকা",
            )
        )

    notices = {}
    for name, lifecycle, label in [
        ("published", "published", "অনুশীলনের ঘোষিত সময়সূচি"),
        ("draft", "draft", "শুধু Admin-এর খসড়া"),
        ("withdrawn", "withdrawn", "প্রত্যাহার করা অনুশীলন বিজ্ঞপ্তি"),
    ]:
        notice = Notice(
            id=key("notice:" + name),
            title="কাল্পনিক ডেমো — " + label,
            body=DISCLAIMER
            + " এটি স্বয়ংক্রিয় walkthrough fixture। example.com শুধুই সংরক্ষিত নমুনা ঠিকানা, সরকারি citation নয়। Review status-ও অনুশীলনের অংশ।",
            source_url=SOURCE,
            publisher="কাল্পনিক ডেমো প্রকাশক — সরকারি নয়",
            lifecycle=lifecycle,
            is_demo=True,
            published_at=instant,
            verification_status="unverified" if lifecycle == "draft" else "verified",
            verified_by=None if lifecycle == "draft" else admin.id,
            verified_at=None if lifecycle == "draft" else instant,
            created_by=admin.id,
            updated_by=admin.id,
        )
        db.add(notice)
        db.flush()
        notices[name] = notice
        audit(notice)
    ancestor_ids = [
        str(locations[n].id) for n in ("division", "district", "city", "ward")
    ]
    windows = [
        ("first", "published", "announced", "published", 2, 3),
        ("second", "published", "announced", "published", 2.5, 3.5),
        ("cancelled", "published", "cancelled", "published", 26, 27),
        ("draft", "draft", "announced", "draft", 4, 5),
    ]
    for name, notice_name, status, lifecycle, start, end in windows:
        schedule = Schedule(
            id=key("schedule:" + name),
            notice_id=notices[notice_name].id,
            location_id=area.id,
            starts_at=instant + timedelta(hours=start),
            ends_at=instant + timedelta(hours=end),
            status=status,
            lifecycle=lifecycle,
            is_demo=True,
            created_by=admin.id,
            updated_by=admin.id,
            category="fictional_demo",
            coverage=[
                {
                    "id": str(area.id),
                    "name_bn": area.name_bn,
                    "ancestor_ids": ancestor_ids,
                }
            ],
        )
        db.add(schedule)
        audit(schedule)

    # This simulated neighbor cannot log in; no extra public/default password.
    neighbor = User(
        id=key("neighbor"),
        email="fictional-neighbor@example.com",
        display_name="কাল্পনিক ডেমো প্রতিবেশী",
        role="user",
        is_active=False,
        password_hash=hash_password(uuid.uuid4().hex),
    )
    db.add(neighbor)
    db.flush()
    midnight = datetime.combine(
        instant.astimezone(ZoneInfo("Asia/Dhaka")).date(),
        datetime.min.time(),
        tzinfo=ZoneInfo("Asia/Dhaka"),
    ) - timedelta(days=1)
    episodes = [
        (
            "recent",
            user,
            instant - timedelta(minutes=45),
            instant - timedelta(minutes=15),
        ),
        (
            "midnight",
            user,
            midnight - timedelta(minutes=10),
            midnight + timedelta(minutes=20),
        ),
        ("incomplete", user, None, instant - timedelta(days=3)),
        ("neighbor-open", neighbor, instant - timedelta(minutes=20), None),
        (
            "admin-history",
            admin,
            instant - timedelta(minutes=80),
            instant - timedelta(minutes=60),
        ),
    ]
    for name, account, start, end in episodes:
        last = end or instant - timedelta(minutes=5)
        episode = PersonalEpisode(
            id=key("episode:" + name),
            user_id=account.id,
            location_id=area.id,
            started_at=start,
            ended_at=end,
            last_observed_at=last,
            is_open=end is None,
        )
        db.add(episode)
        db.flush()
        observations = []
        if start:
            observations.append(("power_off", start))
        observations.append(("power_back" if end else "still_off", last))
        for index, (kind, observed) in enumerate(observations):
            report = Report(
                id=key(f"report:{name}:{index}"),
                user_id=account.id,
                location_id=area.id,
                episode_id=episode.id,
                kind=kind,
                observed_at=observed,
                idempotency_key=key(f"request:{name}:{index}"),
                note=DISCLAIMER,
                is_demo=True,
                moderation="accepted",
                created_at=observed,
                updated_at=observed,
            )
            db.add(report)
            audit(report)
    db.add(
        Report(
            id=key("pending-report"),
            user_id=neighbor.id,
            location_id=alternate.id,
            kind="power_off",
            observed_at=instant + timedelta(seconds=30),
            idempotency_key=key("pending-request"),
            note=DISCLAIMER + " Clock-skew review example.",
            is_demo=True,
            moderation="pending",
        )
    )
    for name, title, start, end in [
        ("conflict", "কাল্পনিক ডেমো: অনলাইন ক্লাস", 2.25, 3.25),
        ("boundary", "কাল্পনিক ডেমো: ঘোষণার শেষে শুরু", 3.5, 4.5),
    ]:
        activity = Activity(
            id=key("activity:" + name),
            user_id=user.id,
            location_id=area.id,
            title=title,
            starts_at=instant + timedelta(hours=start),
            ends_at=instant + timedelta(hours=end),
        )
        db.add(activity)
        audit(activity)
    event = OutageEvent(
        id=key("event"),
        location_id=area.id,
        started_at=instant - timedelta(days=1, hours=2),
        restored_at=instant - timedelta(days=1, hours=1),
        verified_by=admin.id,
        verified_at=instant,
        start_evidence=DISCLAIMER + " আলাদা অনুশীলন সাক্ষ্য। Schedule থেকে তৈরি নয়।",
        restoration_evidence=DISCLAIMER + " কাল্পনিক restoration সাক্ষ্য।",
    )
    db.add(event)
    audit(event)
    manifest = {
        "dataset": DATASET,
        "is_demo": True,
        "seeded_at": instant.isoformat(),
        "default_location_id": str(area.id),
        "locations": len(hierarchy),
        "notices": 3,
        "schedules": 4,
        "personal_episodes": 5,
        "reports": 10,
        "activities": 2,
        "reviewed_events": 1,
        "official_sources_used": [],
        "disclaimer": DISCLAIMER,
    }
    db.add(
        EvidenceAudit(
            id=key("manifest"),
            actor_id=admin.id,
            entity_id=key("manifest"),
            entity_type="demo_dataset",
            action="demo_dataset_seed",
            snapshot=manifest,
        )
    )
    db.flush()
    return manifest | {"already_seeded": False}


def main():
    settings = get_settings()
    with SessionLocal.begin() as db:
        result = seed_content(settings, db)
    print(
        json.dumps(result, ensure_ascii=True)
    )  # Only public fixture metadata; no credentials.


if __name__ == "__main__":
    try:
        main()
    except (ValueError, SQLAlchemyError):
        raise SystemExit(
            "Demo content refused/failed: require an isolated marked demo DB, the private account pair and empty tables or a valid dataset marker. Existing data preserved; no secrets displayed."
        ) from None
