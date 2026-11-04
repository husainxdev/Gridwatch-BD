"""Read-only source directory. Historical records never become report targets."""

import unicodedata
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.orm import Session

from .db import get_db
from .models import DirectoryDataset, DirectoryPlace, Location

router = APIRouter(prefix="/api/directory", tags=["source directory"])


def dataset(db):
    return db.scalar(
        select(DirectoryDataset)
        .order_by(DirectoryDataset.created_at.desc(), DirectoryDataset.id)
        .limit(1)
    )


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    item = dataset(db)
    if not item:
        return {"available": False, "counts": {}, "sources": [], "review_queue": []}
    counts = dict(
        db.execute(
            select(DirectoryPlace.branch, func.count())
            .where(DirectoryPlace.dataset_id == item.id)
            .group_by(DirectoryPlace.branch)
        ).all()
    )
    return {
        "available": True,
        "counts": counts,
        "imported_at": item.created_at,
        "checksum": item.checksum,
        "reviewed_at": item.review["reviewed_at"],
        "sources": item.sources,
        "review_queue": item.ancillary["review_queue"],
        "electricity_references": item.ancillary["electricity_references"],
        "warning": "Census 2022 is a separate historical supplied extraction; no current ward or electrical crosswalk is approved.",
    }


def breadcrumbs(db, ids):
    result = {key: [] for key in ids}
    if not ids:
        return result
    rows = db.execute(
        text("""
      WITH RECURSIVE paths AS (
        SELECT id AS origin,id,parent_id,name_bn,name_en,kind,0 AS depth,ARRAY[id] AS visited FROM directory_places WHERE id=ANY(:ids)
        UNION ALL
        SELECT p.origin,a.id,a.parent_id,a.name_bn,a.name_en,a.kind,p.depth+1,p.visited||a.id
        FROM paths p JOIN directory_places a ON a.id=p.parent_id
        WHERE NOT a.id=ANY(p.visited) AND p.depth < 20
      ) SELECT origin,id,name_bn,name_en,kind FROM paths WHERE depth>0 ORDER BY depth DESC
    """),
        {"ids": ids},
    ).all()
    for origin, key, bn, en, kind in rows:
        result[origin].append({"id": key, "name": bn or en, "kind": kind})
    return result


def render(row, current_status, path):
    historic = row.branch == "census2022"
    return {
        "id": row.id,
        "parent_id": row.parent_id,
        "branch": row.branch,
        "external_id": row.external_id,
        "name_bn": row.name_bn,
        "name_en": row.name_en,
        "kind": row.kind,
        "source_id": row.source_id,
        "source_url": row.source_url,
        "review_status": row.review_status,
        "census_year": row.original.get("census_year"),
        "pdf_page_claimed": row.original.get("pdf_page"),
        "bbs_code_segments": row.original.get("bbs_code_segments"),
        "location_id": row.location_id,
        "reportable": not historic
        and row.review_status == "source_checked"
        and current_status == "verified",
        "current_verification_status": current_status,
        "ancestors": path,
        "warning": "২০২২ সালের প্রদত্ত উদ্ধৃতি; বর্তমান সীমানা বা PDF-এর প্রতিটি পৃষ্ঠার মিল যাচাইকৃত নয়।"
        if historic
        else "প্রশাসনিক পরিচয়; বিদ্যুৎ সরবরাহের আওতা নয়।",
    }


@router.get("")
def places(
    db: Session = Depends(get_db),
    branch: Literal["portal", "census2022"] = "portal",
    search: str = Query("", max_length=100),
    parent_id: uuid.UUID | None = None,
    roots_only: bool = False,
    kind: str | None = Query(None, max_length=32),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    item = dataset(db)
    if not item:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    stmt = (
        select(DirectoryPlace, Location.verification_status)
        .outerjoin(Location, Location.id == DirectoryPlace.location_id)
        .where(DirectoryPlace.dataset_id == item.id, DirectoryPlace.branch == branch)
    )
    if parent_id:
        parent = db.get(DirectoryPlace, parent_id)
        if not parent or parent.branch != branch or parent.dataset_id != item.id:
            raise HTTPException(422, "Choose a parent in the same source snapshot")
        stmt = stmt.where(DirectoryPlace.parent_id == parent_id)
    if roots_only:
        stmt = stmt.where(DirectoryPlace.parent_id.is_(None))
    if kind:
        allowed = (
            {"division", "district", "upazila", "city_corporation", "ward", "union"}
            if branch == "portal"
            else {
                "district",
                "upazila",
                "city_corporation",
                "census_thana",
                "ward_segment",
                "mauza_segment",
                "mahalla",
                "village",
                "municipality",
                "cantonment",
                "union",
            }
        )
        if kind not in allowed:
            raise HTTPException(422, "Unsupported type in this source snapshot")
        stmt = stmt.where(DirectoryPlace.kind == kind)
    term = " ".join(unicodedata.normalize("NFKC", search).split())
    for word in term.split():
        value = (
            "%"
            + word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        stmt = stmt.where(
            or_(
                DirectoryPlace.name_bn.ilike(value, escape="\\"),
                DirectoryPlace.name_en.ilike(value, escape="\\"),
                cast(DirectoryPlace.aliases, String).ilike(value, escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(
            func.coalesce(DirectoryPlace.name_bn, DirectoryPlace.name_en),
            DirectoryPlace.id,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    paths = breadcrumbs(db, [row.id for row, _ in rows])
    child_counts = (
        dict(
            db.execute(
                select(DirectoryPlace.parent_id, func.count())
                .where(DirectoryPlace.parent_id.in_([row.id for row, _ in rows]))
                .group_by(DirectoryPlace.parent_id)
            ).all()
        )
        if rows
        else {}
    )
    return {
        "items": [
            render(row, status, paths[row.id])
            | {"children_count": child_counts.get(row.id, 0)}
            for row, status in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{place_id}")
def detail(place_id: uuid.UUID, db: Session = Depends(get_db)):
    row = db.get(DirectoryPlace, place_id)
    if not row:
        raise HTTPException(404, "Directory record not found")
    current = db.get(Location, row.location_id) if row.location_id else None
    item = db.get(DirectoryDataset, row.dataset_id)
    source = next(s for s in item.sources if s["id"] == row.source_id)
    return render(
        row,
        current.verification_status if current else None,
        breadcrumbs(db, [row.id])[row.id],
    ) | {"source": source, "original": row.original}
