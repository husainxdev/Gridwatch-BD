"""Token and password primitives; never persist raw refresh or reset tokens."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .models import RefreshSession, User

bearer = HTTPBearer(auto_error=False)


def now():
    return datetime.now(timezone.utc)


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def secret_key():
    key = get_settings().jwt_secret
    if not key or len(key) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    return key


def hash_password(value: str):
    if not 8 <= len(value.encode("utf-8")) <= 72:
        raise ValueError("Password must be 8–72 UTF-8 bytes")
    return bcrypt.hashpw(value.encode(), bcrypt.gensalt()).decode()


def check_password(value: str, hashed: str):
    if len(value.encode()) > 72:
        return False
    return bcrypt.checkpw(value.encode(), hashed.encode())


def access_token(user: User, session_id: uuid.UUID):
    issued = now()
    return jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role,
            "sid": str(session_id),
            "type": "access",
            "iat": issued,
            "exp": issued + timedelta(minutes=15),
        },
        secret_key(),
        algorithm="HS256",
    )


def new_refresh(db: Session, user: User, family: uuid.UUID | None = None):
    raw = secrets.token_urlsafe(48)
    session = RefreshSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=digest(raw),
        family_id=family or uuid.uuid4(),
        expires_at=now() + timedelta(days=7),
    )
    db.add(session)
    return raw, session.id


def revoke_family(db: Session, family: uuid.UUID):
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.family_id == family, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now())
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(401, "Sign in required")
    try:
        claims = jwt.decode(
            credentials.credentials,
            secret_key(),
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
        if claims.get("type") != "access":
            raise ValueError("Wrong token type")
        uid = uuid.UUID(claims["sub"])
        sid = uuid.UUID(claims["sid"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid or expired token") from None
    session = db.get(RefreshSession, sid)
    if (
        not session
        or session.user_id != uid
        or session.revoked_at
        or session.expires_at < now()
    ):
        raise HTTPException(401, "Session expired")
    user = db.get(User, uid)
    if user is None or not user.is_active:
        raise HTTPException(401, "Account inactive")
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def require_cookie_origin(request: Request):
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin != settings.frontend_url.rstrip("/"):
        raise HTTPException(403, "Untrusted origin")
    csrf = request.cookies.get("gridwatch_csrf")
    header = request.headers.get("x-csrf-token")
    if not csrf or not header or not secrets.compare_digest(csrf, header):
        raise HTTPException(403, "CSRF token required")


def put_auth_cookies(response, refresh: str, csrf: str):
    secure = get_settings().app_env == "production"
    response.set_cookie(
        "gridwatch_refresh",
        refresh,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/api/auth",
        max_age=7 * 86400,
    )
    response.set_cookie(
        "gridwatch_csrf",
        csrf,
        httponly=False,
        secure=secure,
        samesite="strict",
        path="/",
        max_age=7 * 86400,
    )


def clear_auth_cookies(response):
    for name in ("gridwatch_refresh", "gridwatch_csrf"):
        response.delete_cookie(
            name, path="/" if name == "gridwatch_csrf" else "/api/auth"
        )
