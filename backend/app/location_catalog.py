"""Reviewed administrative directory, not outage/feeder seed data.

No network request is made at startup. The reviewed source excerpts, retrieval
hashes and dates travel with the application. The caller owns the transaction.
"""

import json
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import func, or_, select, text

from .config import get_settings
from .models import Location

CATALOG = Path(__file__).resolve().parents[2] / "data/sylhet-city-locations.v1.json"


def load_catalog():
    data = json.loads(CATALOG.read_text())
    if data["version"] != 1 or len(data["locations"]) != 45:
        raise ValueError("Unsupported administrative catalog")
    sources = {source["key"]: source for source in data["sources"]}
    reviewed = datetime.fromisoformat(data["reviewed_at"])
    if not reviewed.tzinfo:
        raise ValueError("Catalog requires an aware verification timestamp")
    seen = set()
    allowed = {
        "division": {None},
        "district": {"division"},
        "city_corporation": {"district"},
        "ward": {"city_corporation"},
    }
    kinds = {}
    for row in data["locations"]:
        source = sources[row["source"]]
        parsed = urlsplit(source["url"])
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"scc.gov.bd", "sylhetdiv.gov.bd"}
            or parsed.username
            or parsed.password
        ):
            raise ValueError(
                "Catalog source must be an original reviewed official page"
            )
        if (
            row["key"] in seen
            or row["parent"] not in seen | {None}
            or kinds.get(row["parent"]) not in allowed[row["kind"]]
        ):
            raise ValueError("Invalid catalog hierarchy")
        seen.add(row["key"])
        kinds[row["key"]] = row["kind"]
    return data, sources, reviewed


def import_catalog(db, *, only_if_empty=False):
    if get_settings().demo_instance:
        raise ValueError(
            "A real directory cannot be imported into a fictional instance"
        )
    db.execute(text("SELECT pg_advisory_xact_lock(34001)"))
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    if only_if_empty and db.scalar(select(Location.id).limit(1)):
        return {"created": 0, "preserved": 0, "skipped_nonempty": True}
    data, sources, reviewed = load_catalog()
    nodes, created, preserved = {}, 0, 0
    for row in data["locations"]:
        parent = nodes[row["parent"]].id if row["parent"] else None
        key = uuid.uuid5(
            uuid.NAMESPACE_URL, "https://gridwatch.invalid/catalog/" + row["key"]
        )
        bn = unicodedata.normalize("NFKC", row["name_bn"]).strip()
        en = row["name_en"].strip()
        suffixes = {
            "division": (" বিভাগ", " Division"),
            "district": (" জেলা", " District"),
            "city_corporation": (" সিটি কর্পোরেশন", " City Corporation"),
        }
        bn_suffix, en_suffix = suffixes.get(row["kind"], ("", ""))
        bn_names = (
            {bn.lower(), bn.removesuffix(bn_suffix).strip().lower()}
            if bn_suffix
            else {bn.lower()}
        )
        en_names = (
            {en.lower(), en.removesuffix(en_suffix).strip().lower()}
            if en_suffix
            else {en.lower()}
        )
        # Reuse an existing exact identity without silently changing its review,
        # names, aliases, source, version or historical descendants.
        matches = db.scalars(
            select(Location).where(
                or_(
                    Location.id == key,
                    Location.slug == row["key"],
                    (Location.kind == row["kind"])
                    & (Location.parent_id == parent)
                    & or_(
                        func.lower(func.btrim(Location.name_bn)).in_(bn_names),
                        func.lower(func.btrim(Location.name_en)).in_(en_names),
                    ),
                )
            )
        ).all()
        if len(matches) > 1:
            raise ValueError(
                "Catalog identity conflicts with existing locations; no changes committed"
            )
        if matches:
            item = matches[0]
            if item.parent_id != parent or item.kind != row["kind"]:
                raise ValueError("Catalog hierarchy conflicts with an existing record")
            preserved += 1
        else:
            item = Location(
                id=key,
                slug=row["key"],
                name_bn=bn,
                name_en=en,
                kind=row["kind"],
                parent_id=parent,
                aliases=[unicodedata.normalize("NFKC", a) for a in row["aliases"]],
                verification_status="verified",
                source_url=sources[row["source"]]["url"],
                verified_at=reviewed,
            )
            db.add(item)
            db.flush()
            created += 1
        nodes[row["key"]] = item
    return {
        "created": created,
        "preserved": preserved,
        "skipped_nonempty": False,
        "catalog_id": data["catalog_id"],
    }
