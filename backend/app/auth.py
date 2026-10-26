import secrets
import smtplib
import ssl
import uuid
import jwt
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .models import PasswordReset, RefreshSession, User
from .security import (
    access_token,
    check_password,
    clear_auth_cookies,
    current_user,
    digest,
    hash_password,
    new_refresh,
    now,
    put_auth_cookies,
    require_cookie_origin,
    revoke_family,
    secret_key,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class Credentials(BaseModel):
    email: EmailStr
    password: str


class Register(Credentials):
    display_name: str = Field(min_length=2, max_length=100)


class ResetRequest(BaseModel):
    email: EmailStr


class ResetConfirm(BaseModel):
    token: str
    password: str


def user_dict(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


def signed_in(response, db, user, family=None):
    refresh, session_id = new_refresh(db, user, family)
    put_auth_cookies(response, refresh, secrets.token_urlsafe(32))
    db.commit()
    return {
        "access_token": access_token(user, session_id),
        "token_type": "bearer",
        "user": user_dict(user),
    }


@router.post("/register", status_code=201)
def register(body: Register, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    try:
        password = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    user = User(
        email=email,
        display_name=body.display_name.strip(),
        password_hash=password,
        role="user",
    )
    if not user.display_name:
        raise HTTPException(422, "Name required")
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered") from None
    return signed_in(response, db, user)


@router.post("/login")
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    if (
        not user
        or not user.is_active
        or not check_password(body.password, user.password_hash)
    ):
        raise HTTPException(401, "Invalid credentials")
    return signed_in(response, db, user)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_dict(user)


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    require_cookie_origin(request)
    raw = request.cookies.get("gridwatch_refresh")
    if not raw:
        raise HTTPException(401, "Session expired")
    session = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == digest(raw))
        .with_for_update()
    )
    if not session:
        raise HTTPException(401, "Session expired")
    if session.revoked_at is not None:
        revoke_family(db, session.family_id)
        db.commit()
        raise HTTPException(401, "Session revoked")
    if session.expires_at < now():
        raise HTTPException(401, "Session expired")
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Account inactive")
    session.revoked_at = now()
    return signed_in(response, db, user, session.family_id)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    require_cookie_origin(request)
    raw = request.cookies.get("gridwatch_refresh")
    if raw:
        session = db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == digest(raw))
        )
        if session:
            revoke_family(db, session.family_id)
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        try:
            claims = jwt.decode(
                authorization[7:],
                secret_key(),
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            if claims.get("type") == "access":
                access_session = db.get(RefreshSession, uuid.UUID(claims["sid"]))
                if access_session and str(access_session.user_id) == claims.get("sub"):
                    revoke_family(db, access_session.family_id)
        except (jwt.PyJWTError, ValueError, KeyError):
            pass
    db.commit()
    clear_auth_cookies(response)


@router.post("/password-reset/request", status_code=202)
def request_reset(body: ResetRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.smtp_host or (
        settings.app_env == "production"
        and (
            not settings.smtp_starttls
            or not settings.smtp_username
            or not settings.smtp_password
        )
    ):
        raise HTTPException(503, "Password reset mail is not configured securely")
    user = db.scalar(
        select(User).where(
            User.email == body.email.lower().strip(), User.is_active.is_(True)
        )
    )
    if user:
        raw = secrets.token_urlsafe(48)
        db.add(
            PasswordReset(
                user_id=user.id,
                token_hash=digest(raw),
                expires_at=now() + timedelta(minutes=20),
            )
        )
        message = EmailMessage()
        message["Subject"] = "GridWatch BD password reset"
        message["From"] = settings.mail_from
        message["To"] = user.email
        message.set_content(
            "Reset your password within 20 minutes: "
            + settings.frontend_url.rstrip("/")
            + "/reset?token="
            + quote(raw)
        )
        try:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=8
            ) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username and settings.smtp_password:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            db.rollback()
            raise HTTPException(503, "Mail service unavailable") from None
        db.commit()
    return {"message": "If the account exists, a reset link has been sent."}


@router.post("/password-reset/confirm")
def confirm_reset(body: ResetConfirm, db: Session = Depends(get_db)):
    record = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.token_hash == digest(body.token))
        .with_for_update()
    )
    if not record or record.used_at or record.expires_at < now():
        raise HTTPException(400, "Invalid or expired reset link")
    try:
        hashed = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Invalid reset link")
    user.password_hash = hashed
    record.used_at = now()
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now())
    )
    db.commit()
    return {"message": "Password changed. Sign in again."}
