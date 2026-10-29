"""Admin-managed source claims. No electrical coverage inferred from a location."""

import unicodedata
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import String, or_, select, text
from sqlalchemy.orm import Session

from .api import find, list_page
from .db import get_db
from .evidence import audit, serialize
from .models import ElectricityOffice, EvidenceAudit, FeederMapping, Location, User
from .security import admin_user, now

router = APIRouter(prefix="/api/admin/registry", tags=["reviewed electricity registry"])


class SourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(default=1, ge=1)
    source_url: HttpUrl

    @field_validator("source_url")
    @classmethod
    def https(cls, value):
        if value.scheme != "https":
            raise ValueError("Original HTTPS evidence required")
        return value

    @field_validator(
        "name_bn", "name_en", "feeder_name", "coverage_description", check_fields=False
    )
    @classmethod
    def normalize(cls, value, info):
        value = " ".join(unicodedata.normalize("NFKC", value).split())
        minimum, maximum = (
            (12, 1000) if info.field_name == "coverage_description" else (2, 160)
        )
        if not minimum <= len(value) <= maximum:
            raise ValueError(
                f"Normalized value must contain {minimum}–{maximum} characters"
            )
        return value


class OfficeBody(SourceBody):
    name_bn: str = Field(min_length=2, max_length=160)
    name_en: str = Field(min_length=2, max_length=160)


class MappingBody(SourceBody):
    office_id: uuid.UUID
    location_id: uuid.UUID
    feeder_name: str = Field(min_length=2, max_length=160)
    coverage_description: str = Field(min_length=12, max_length=1000)


class ReviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=500)


def validate_mapping(db, body):
    office = find(db, ElectricityOffice, body.office_id)
    area = find(db, Location, body.location_id)
    if (
        not office.is_active
        or office.verification_status != "verified"
        or area.verification_status != "verified"
    ):
        raise HTTPException(
            422, "An active reviewed office and verified location are required"
        )


def lock(db, model, key, version):
    # Registry transactions have one lock order, including office invalidation.
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    item = find(db, model, key)
    if item.version != version:
        raise HTTPException(409, "Registry record changed; reload first")
    return item


def payload(body):
    return body.model_dump(exclude={"version"}) | {"source_url": str(body.source_url)}


@router.get("/{entity}")
def records(
    entity: Literal["offices", "mappings"],
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
    search: str = Query("", max_length=160),
    status: Literal["verified", "unverified"] | None = None,
    active: bool | None = None,
    office_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    sort: Literal["newest", "oldest", "name", "time"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    model = ElectricityOffice if entity == "offices" else FeederMapping
    name = model.name_bn if entity == "offices" else model.feeder_name
    stmt = select(model)
    if search:
        predicates = [name.ilike("%" + search + "%"), model.id.cast(String) == search]
        if entity == "offices":
            predicates.append(model.name_en.ilike("%" + search + "%"))
        stmt = stmt.where(or_(*predicates))
    if status:
        stmt = stmt.where(model.verification_status == status)
    if active is not None:
        stmt = stmt.where(model.is_active == active)
    if entity == "mappings":
        if office_id:
            stmt = stmt.where(FeederMapping.office_id == office_id)
        if location_id:
            stmt = stmt.where(FeederMapping.location_id == location_id)
    elif office_id or location_id:
        raise HTTPException(422, "Coverage filter only applies to mappings")
    ordering = {
        "newest": model.created_at.desc(),
        "oldest": model.created_at,
        "name": name,
        "time": model.updated_at,
    }[sort]
    result = list_page(
        db, stmt.order_by(ordering, model.id), page, page_size, serialize
    )
    if entity == "mappings" and result["items"]:
        ids = [r["id"] for r in result["items"]]
        details = {
            r.id: r
            for r in db.execute(
                select(
                    FeederMapping.id,
                    ElectricityOffice.name_bn,
                    ElectricityOffice.is_active,
                    ElectricityOffice.verification_status,
                    Location.name_bn.label("location_name"),
                    Location.verification_status.label("location_status"),
                )
                .join(
                    ElectricityOffice, ElectricityOffice.id == FeederMapping.office_id
                )
                .join(Location, Location.id == FeederMapping.location_id)
                .where(FeederMapping.id.in_(ids))
            )
        }
        for r in result["items"]:
            d = details[r["id"]]
            r.update(
                office_name=d.name_bn,
                location_name=d.location_name,
                usable=r["is_active"]
                and r["verification_status"] == "verified"
                and d.is_active
                and d.verification_status == "verified"
                and d.location_status == "verified",
            )
    return result


@router.post("/offices", status_code=201)
def create_office(
    body: OfficeBody, db: Session = Depends(get_db), actor: User = Depends(admin_user)
):
    item = ElectricityOffice(**payload(body))
    db.add(item)
    db.flush()
    audit(db, actor, item, "create")
    db.commit()
    return serialize(item)


@router.post("/mappings", status_code=201)
def create_mapping(
    body: MappingBody, db: Session = Depends(get_db), actor: User = Depends(admin_user)
):
    db.execute(text("SELECT pg_advisory_xact_lock(34002)"))
    validate_mapping(db, body)
    item = FeederMapping(**payload(body))
    db.add(item)
    db.flush()
    audit(db, actor, item, "create")
    db.commit()
    return serialize(item)


def invalidate_mappings(db, office_id):
    for item in db.scalars(
        select(FeederMapping).where(FeederMapping.office_id == office_id)
    ):
        item.verification_status = "unverified"
        item.verified_by = None
        item.verified_at = None
        item.version += 1


def revise(db, item, body, actor):
    audit(db, actor, item, "before_edit")
    for k, v in payload(body).items():
        setattr(item, k, v)
    item.version += 1
    item.verification_status = "unverified"
    item.verified_at = None
    item.verified_by = None
    if isinstance(item, ElectricityOffice):
        invalidate_mappings(db, item.id)
    db.commit()
    return serialize(item)


@router.put("/offices/{key}")
def edit_office(
    key: uuid.UUID,
    body: OfficeBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    return revise(db, lock(db, ElectricityOffice, key, body.version), body, actor)


@router.put("/mappings/{key}")
def edit_mapping(
    key: uuid.UUID,
    body: MappingBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    item = lock(db, FeederMapping, key, body.version)
    validate_mapping(db, body)
    return revise(db, item, body, actor)


@router.post("/{entity}/{key}/{action}")
def review(
    entity: Literal["offices", "mappings"],
    key: uuid.UUID,
    action: Literal["verify", "deactivate", "activate"],
    body: ReviewBody,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    model = ElectricityOffice if entity == "offices" else FeederMapping
    item = lock(db, model, key, body.version)
    db.info["audit_reason"] = body.reason
    audit(db, actor, item, action)
    if action == "verify":
        if not item.is_active:
            raise HTTPException(422, "Activate before review")
        if entity == "mappings":
            validate_mapping(db, item)
        item.verification_status = "verified"
        item.verified_by = actor.id
        item.verified_at = now()
    else:
        item.is_active = action == "activate"
        item.verification_status = "unverified"
        item.verified_by = None
        item.verified_at = None
        if entity == "offices":
            invalidate_mappings(db, key)
    item.version += 1
    db.commit()
    return serialize(item)


@router.delete("/{entity}/{key}", status_code=204)
def remove(
    entity: Literal["offices", "mappings"],
    key: uuid.UUID,
    version: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    actor: User = Depends(admin_user),
):
    model = ElectricityOffice if entity == "offices" else FeederMapping
    item = lock(db, model, key, version)
    if item.verification_status == "verified" or db.scalar(
        select(EvidenceAudit.id)
        .where(EvidenceAudit.entity_id == key, EvidenceAudit.action == "verify")
        .limit(1)
    ):
        raise HTTPException(409, "Preserve reviewed evidence; deactivate instead")
    if entity == "offices" and db.scalar(
        select(FeederMapping.id).where(FeederMapping.office_id == key).limit(1)
    ):
        raise HTTPException(409, "Office is referenced by mappings; deactivate instead")
    audit(db, actor, item, "delete")
    db.delete(item)
    db.commit()


def invalidate_location_mappings(db, location_id):
    for item in db.scalars(
        select(FeederMapping).where(FeederMapping.location_id == location_id)
    ):
        item.verification_status = "unverified"
        item.verified_by = None
        item.verified_at = None
        item.version += 1
