from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .models import DemoArea
from .auth import router as auth_router
from .security import secret_key
from .api import router as api_router

settings = get_settings()
secret_key()  # fail startup instead of serving auth with a missing/weak signing secret
app = FastAPI(
    title="GridWatch BD",
    version="0.1.0",
    description="Foundation API. Demo records are not official outage data.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health/live")
def live():
    return {"status": "ok", "service": "gridwatch-bd"}


@app.get("/api/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        if revision != "0001":
            raise HTTPException(503, "Database migration required")
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable or migration required") from None
    return {"status": "ready", "database": "connected", "schema": revision}


@app.get("/api/demo/areas")
def demo_areas(db: Session = Depends(get_db)):
    if not settings.demo_enabled or settings.app_env == "production":
        raise HTTPException(404, "Not found")
    try:
        rows = db.scalars(select(DemoArea).order_by(DemoArea.sort_order)).all()
    except SQLAlchemyError:
        raise HTTPException(503, "Demo database unavailable") from None
    return {
        "data_mode": "demonstration",
        "items": [
            {
                "id": str(r.id),
                "name_bn": r.name_bn,
                "description": r.description,
                "updated_at": r.updated_at,
                "power_status": "unknown",
            }
            for r in rows
        ],
    }


app.include_router(auth_router)
app.include_router(api_router)
