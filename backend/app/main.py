from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .api import router as api_router
from .auth import router as auth_router
from .config import get_settings
from .dashboard import router as dashboard_router
from .db import get_db
from .evidence import router as evidence_router
from .models import DemoArea
from .security import secret_key

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
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    allow_credentials=True,
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
        if revision != "0004":
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
app.include_router(dashboard_router)
app.include_router(evidence_router)
app.include_router(api_router)

# Do not reflect Pydantic's raw input (passwords/reset tokens) in API responses.


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request",
            "fields": [
                {
                    "field": ".".join(map(str, e["loc"])),
                    "message": e["msg"],
                    "code": e["type"],
                }
                for e in exc.errors()
            ],
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse(
        status_code=503, content={"detail": "Database operation unavailable"}
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={"detail": "Record conflicts with an existing or referenced record"},
    )


@app.middleware("http")
async def private_api_cache(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "private, no-store"
    return response
