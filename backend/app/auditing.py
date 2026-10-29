"""Append-only change snapshots for admin mutations in the same transaction."""

from fastapi.encoders import jsonable_encoder
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from .models import (
    ElectricityOffice,
    EvidenceAudit,
    FeederMapping,
    Location,
    Notice,
    OutageEvent,
    Report,
    Schedule,
)


@event.listens_for(Session, "before_flush")
def capture_changes(session, context, instances):
    actor = session.info.get("audit_actor")
    if not actor:
        return
    for item in list(session.dirty) + list(session.deleted):
        if not isinstance(
            item,
            (
                Location,
                Notice,
                Schedule,
                Report,
                OutageEvent,
                ElectricityOffice,
                FeederMapping,
            ),
        ):
            continue
        state = inspect(item)
        changes = {}
        for column in item.__table__.columns:
            if column.name in {"note", "user_id", "idempotency_key", "updated_at"}:
                continue
            history = state.attrs[column.name].history
            if history.has_changes():
                changes[column.name] = {
                    "before": history.deleted[0] if history.deleted else None,
                    "after": getattr(item, column.name),
                }
        if changes or item in session.deleted:
            session.add(
                EvidenceAudit(
                    actor_id=actor,
                    entity_type=item.__tablename__,
                    entity_id=item.id,
                    action="delete_changes" if item in session.deleted else "changes",
                    snapshot=jsonable_encoder(
                        {
                            "changes": changes,
                            "reason": session.info.get("audit_reason"),
                            "deleted_record": {
                                c.name: getattr(item, c.name)
                                for c in item.__table__.columns
                                if c.name not in {"note", "user_id", "idempotency_key"}
                            }
                            if item in session.deleted
                            else None,
                        }
                    ),
                )
            )
