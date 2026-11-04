"""Read the supplied SQLite as data only; import separate source snapshots into PostgreSQL."""

import hashlib
import json
import sqlite3
import unicodedata
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import func, insert, or_, select, text

from .config import get_settings
from .models import DirectoryDataset, DirectoryPlace, Location

ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = ROOT / "data/sylhet-locations.source.sqlite"
REVIEW_FILE = ROOT / "data/sylhet-locations.review.json"
TABLES = {
    "sources",
    "locations",
    "census_locations",
    "review_queue",
    "union_roster_checks",
    "electricity_references",
    "guide",
}


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", value).split()) if value else None


def valid_url(url):
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and (
            host.endswith(".gov.bd")
            or host == "objectstorage.ap-dcc-gazipur-1.oraclecloud15.com"
        )
    )


def topological(rows):
    indexed = {row["id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate directory identity")
    children = {}
    pending = deque()
    for row in rows:
        parent = row["parent_id"]
        if parent is None:
            pending.append(row)
        elif parent not in indexed:
            raise ValueError("Directory parent is missing")
        else:
            children.setdefault(parent, []).append(row)
    result = []
    while pending:
        row = pending.popleft()
        result.append(row)
        pending.extend(children.get(row["id"], []))
    if len(result) != len(rows):
        raise ValueError("Directory has a cycle")
    return result


def read_source(path=SOURCE_FILE):
    path = Path(path).resolve()
    if not 1 <= path.stat().st_size <= 8 * 1024 * 1024:
        raise ValueError("Source file exceeds supported bounds")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.enable_load_extension(False)
        budget = [0]

        def progress():
            budget[0] += 1
            return int(budget[0] > 20000)

        connection.set_progress_handler(progress, 1000)
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Source database failed integrity check")
        connection.row_factory = sqlite3.Row
        payload = {}
        # Only literal allowlisted base tables are read; supplied views/triggers,
        # guide text, SQL snippets and extension declarations are never executed.
        for table in sorted(TABLES):
            kind = connection.execute(
                "SELECT type FROM sqlite_master WHERE name=?", (table,)
            ).fetchone()
            if not kind or kind[0] != "table":
                raise ValueError("Required source object is not a base table")
            rows = connection.execute(
                'SELECT * FROM "' + table + '" LIMIT 20001'
            ).fetchall()
            if len(rows) > 20000:
                raise ValueError("Too many source rows")
            payload[table] = [dict(row) for row in rows]
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Source references are inconsistent")
    finally:
        connection.close()
    sources = {row["id"]: row for row in payload["sources"]}
    if not sources or any(not valid_url(row["url"]) for row in sources.values()):
        raise ValueError("Source links require trusted original HTTPS destinations")
    from .api import KINDS

    for branch, table in [("portal", "locations"), ("census2022", "census_locations")]:
        payload[table] = topological(payload[table])
        kinds = {}
        for row in payload[table]:
            if row["source_id"] not in sources or not row["id"] or len(row["id"]) > 200:
                raise ValueError("Invalid source identity")
            names = [row.get("name_bn"), row.get("name_en")]
            if not any(names) or any(
                name and not 1 <= len(name) <= 160 for name in names
            ):
                raise ValueError("Invalid source name")
            if branch == "portal" and (
                row["kind"] not in KINDS
                or kinds.get(row["parent_id"]) not in KINDS[row["kind"]]
            ):
                raise ValueError(
                    "Portal hierarchy is not a supported administrative relation"
                )
            if branch == "census2022" and (
                row["census_year"] != 2022 or not 1 <= row["pdf_page"] <= 2000
            ):
                raise ValueError("Invalid census snapshot metadata")
            kinds[row["id"]] = row["kind"]
    return checksum, payload


def import_supplied_directory(db, path=SOURCE_FILE):
    if get_settings().demo_instance:
        raise ValueError("Do not mix source directories with fictional instances")
    review = json.loads(REVIEW_FILE.read_text())
    # Verify the approved file before letting SQLite parse its schema at all.
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != review["file_sha256"]:
        raise ValueError("This file has no matching reviewed manifest")
    checksum, data = read_source(path)
    db.execute(text("SELECT pg_advisory_xact_lock(34001)"))
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    existing = db.scalar(
        select(DirectoryDataset).where(DirectoryDataset.checksum == checksum)
    )
    if existing:
        return {
            "already_imported": True,
            "portal": 428,
            "census2022": 5765,
            "created_locations": 0,
            "dataset_id": str(existing.id),
        }
    dataset_id = uuid.uuid5(
        uuid.NAMESPACE_URL, "gridwatch:source-directory:" + checksum
    )
    dataset = DirectoryDataset(
        id=dataset_id,
        checksum=checksum,
        label="সিলেট প্রশাসনিক তালিকা ও প্রদত্ত Census 2022 reference",
        sources=data["sources"],
        review=review,
        ancillary={
            key: data[key]
            for key in [
                "review_queue",
                "union_roster_checks",
                "electricity_references",
                "guide",
            ]
        },
    )
    db.add(dataset)
    db.flush()
    sources = {row["id"]: row for row in data["sources"]}
    reviewed_at = datetime.fromisoformat(review["reviewed_at"])
    current, aliases_by_id, created = {}, {}, 0
    for row in data["locations"]:
        parent = current[row["parent_id"]].id if row["parent_id"] else None
        bn, en = normalized(row["name_bn"]), normalized(row["name_en"])
        variants = {bn}
        suffix = {
            "division": " বিভাগ",
            "district": " জেলা",
            "city_corporation": " সিটি কর্পোরেশন",
        }.get(row["kind"])
        if suffix:
            variants.update({bn + suffix, bn.removesuffix(suffix)})
        match = [
            func.lower(func.btrim(Location.name_bn)).in_([v.lower() for v in variants])
        ]
        if en:
            en_suffix = {"division": " Division", "district": " District"}.get(
                row["kind"], ""
            )
            english = {en, en + en_suffix} if en_suffix else {en}
            match.append(
                func.lower(func.btrim(Location.name_en)).in_(
                    [v.lower() for v in english]
                )
            )
        identity = uuid.uuid5(
            uuid.NAMESPACE_URL, "gridwatch:portal-location:" + row["id"]
        )
        matches = db.scalars(
            select(Location).where(
                or_(
                    Location.id == identity,
                    (Location.kind == row["kind"])
                    & (Location.parent_id == parent)
                    & or_(*match),
                )
            )
        ).all()
        if len(matches) > 1:
            raise ValueError("Ambiguous existing location; no source changes committed")
        row_review = review["portal_rows"][row["id"]]
        ancestors = aliases_by_id.get(row["parent_id"], [])
        aliases = list(
            dict.fromkeys(
                [
                    value
                    for value in [
                        bn,
                        en,
                        row["id"].replace("/", " "),
                        " ".join([*ancestors, bn]),
                    ]
                    if value and 2 <= len(value) <= 160
                ]
            )
        )
        aliases_by_id[row["id"]] = [*ancestors, bn]
        if matches:
            item = matches[0]
            if item.kind != row["kind"] or item.parent_id != parent:
                raise ValueError(
                    "Existing location hierarchy differs from the supplied source"
                )
        else:
            checked = row_review["status"] == "source_checked"
            item = Location(
                id=identity,
                name_bn=bn,
                name_en=en,
                parent_id=parent,
                kind=row["kind"],
                slug="directory-" + identity.hex,
                aliases=aliases,
                verification_status="verified" if checked else "unverified",
                source_url=sources[row["source_id"]]["url"],
                verified_at=reviewed_at if checked else None,
            )
            db.add(item)
            db.flush()
            created += 1
        current[row["id"]] = item
    records = []
    for branch, table in [("portal", "locations"), ("census2022", "census_locations")]:
        for row in data[table]:

            def key(external, snapshot=branch):
                return uuid.uuid5(dataset_id, snapshot + ":" + external)

            url = sources[row["source_id"]]["url"]
            aliases = []
            if branch == "census2022":
                url += "#page=" + str(row["pdf_page"])
                for token, spellings in review.get("census_search_aliases", {}).items():
                    if token in row["name_en"].lower():
                        aliases.extend(spellings)
            else:
                aliases = current[row["id"]].aliases
            records.append(
                {
                    "id": key(row["id"]),
                    "dataset_id": dataset_id,
                    "branch": branch,
                    "external_id": row["id"],
                    "parent_id": key(row["parent_id"]) if row["parent_id"] else None,
                    "kind": row["kind"],
                    "name_bn": normalized(row.get("name_bn")),
                    "name_en": normalized(row.get("name_en")),
                    "aliases": [normalized(value) for value in aliases],
                    "source_id": row["source_id"],
                    "source_url": url,
                    "review_status": review["portal_rows"][row["id"]]["status"]
                    if branch == "portal"
                    else "historical",
                    "location_id": current[row["id"]].id
                    if branch == "portal"
                    else None,
                    "original": row,
                }
            )
    for start in range(0, len(records), 500):
        db.execute(insert(DirectoryPlace), records[start : start + 500])
    return {
        "already_imported": False,
        "portal": len(data["locations"]),
        "census2022": len(data["census_locations"]),
        "created_locations": created,
        "dataset_id": str(dataset_id),
    }
