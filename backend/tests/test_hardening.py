from datetime import UTC

from fastapi.testclient import TestClient

from app import limiting
from app.config import get_settings
from app.main import app


def test_privileged_signup_fields_rejected_without_secret_echo():
    response = TestClient(app).post(
        "/api/auth/register",
        json={
            "email": "person@example.com",
            "display_name": "Person",
            "password": "private-password",
            "role": "admin",
        },
    )
    assert response.status_code == 422
    assert "private-password" not in response.text
    assert any(f["field"] == "body.role" for f in response.json()["fields"])


def test_rate_limit_controlled_clock(monkeypatch):
    limiting._buckets.clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_rate_limit", 2)
    monkeypatch.setattr(settings, "auth_rate_window_seconds", 60)
    clock = [100.0]
    monkeypatch.setattr(limiting, "monotonic", lambda: clock[0])
    client = TestClient(app)
    body = {"email": "absent@example.com", "password": "wrong-password"}
    assert client.post("/api/auth/login", json=body).status_code == 401
    assert client.post("/api/auth/login", json=body).status_code == 401
    response = client.post("/api/auth/login", json=body)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    clock[0] += 61
    assert client.post("/api/auth/login", json=body).status_code == 401
    limiting._buckets.clear()


def test_cors_preflight_auth_headers():
    response = TestClient(app).options(
        "/api/auth/refresh",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,x-csrf-token",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_location_hierarchy_aliases_and_duplicates():
    import uuid
    from types import SimpleNamespace

    from app.security import admin_user

    client = TestClient(app)
    app.dependency_overrides[admin_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    try:
        suffix = uuid.uuid4().hex

        def create(kind, parent=None):
            response = client.post(
                "/api/admin/locations",
                json={
                    "name_bn": kind + suffix,
                    "name_en": kind + suffix,
                    "kind": kind,
                    "slug": kind.replace("_", "-") + "-" + suffix,
                    "parent_id": parent,
                    "aliases": ["Alias " + suffix],
                },
            )
            assert response.status_code == 201, response.text
            return response.json()

        root = create("division")
        district = create("district", root["id"])
        city = create("city_corporation", district["id"])
        ward = create("ward", city["id"])
        assert (
            client.get("/api/locations?roots_only=true").json()["items"][0]["parent_id"]
            is None
        )
        assert (
            client.get("/api/locations/" + city["id"] + "/children").json()["items"][0][
                "id"
            ]
            == ward["id"]
        )
        assert [
            x["id"]
            for x in client.get("/api/locations/" + ward["id"] + "/ancestors").json()[
                "items"
            ]
        ] == [root["id"], district["id"], city["id"]]
        assert client.get("/api/locations?search=" + ward["id"]).json()["total"] == 1
        assert (
            client.get("/api/locations?search=Alias%20" + suffix).json()["total"] == 4
        )
        payload = {
            k: city[k] for k in ["name_bn", "name_en", "slug", "parent_id", "aliases"]
        }
        payload["kind"] = "upazila"
        assert (
            client.put("/api/admin/locations/" + city["id"], json=payload).status_code
            == 422
        )
        payload = {
            k: root[k] for k in ["name_bn", "name_en", "kind", "parent_id", "aliases"]
        }
        payload["slug"] = "duplicate-" + suffix
        payload["name_en"] = payload["name_en"].upper()
        assert client.post("/api/admin/locations", json=payload).status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_bcrypt_utf8_boundary():
    import pytest

    from app.security import check_password, hash_password

    password = "অ" * 24
    assert len(password.encode()) == 72
    assert check_password(password, hash_password(password))
    with pytest.raises(ValueError):
        hash_password(password + "a")
    with pytest.raises(ValueError):
        hash_password("short")


def test_concurrent_refresh_fails_closed():
    import uuid
    from concurrent.futures import ThreadPoolExecutor

    from app.config import get_settings

    origin = get_settings().frontend_url
    client = TestClient(app, headers={"Origin": origin})
    registration = client.post(
        "/api/auth/register",
        json={
            "email": uuid.uuid4().hex + "@example.com",
            "display_name": "Concurrent",
            "password": "valid-password",
        },
    )
    assert registration.status_code == 201
    cookies = dict(client.cookies)

    def rotate(_):
        with TestClient(
            app,
            headers={"Origin": origin, "X-CSRF-Token": cookies["gridwatch_csrf"]},
            cookies=cookies,
        ) as other:
            return other.post("/api/auth/refresh")

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(rotate, range(2)))
    assert sorted(r.status_code for r in responses) == [200, 401]
    winner = next(r for r in responses if r.status_code == 200)
    assert (
        client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer " + winner.json()["access_token"]},
        ).status_code
        == 401
    )


def test_tampered_and_expired_tokens():
    import uuid
    from datetime import datetime, timedelta

    import jwt

    from app.security import secret_key

    client = TestClient(app)
    result = client.post(
        "/api/auth/register",
        json={
            "email": uuid.uuid4().hex + "@example.com",
            "display_name": "Expiry",
            "password": "valid-password",
        },
    )
    token = result.json()["access_token"]
    claims = jwt.decode(token, secret_key(), algorithms=["HS256"])
    claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
    expired = jwt.encode(claims, secret_key(), algorithm="HS256")
    assert (
        client.get(
            "/api/auth/me", headers={"Authorization": "Bearer " + expired}
        ).status_code
        == 401
    )
    tampered = jwt.encode(
        claims, "different-secret-not-the-server-secret", algorithm="HS256"
    )
    assert (
        client.get(
            "/api/auth/me", headers={"Authorization": "Bearer " + tampered}
        ).status_code
        == 401
    )


def test_expired_refresh_and_reset_and_disabled_user(monkeypatch):
    import secrets
    import uuid
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import PasswordReset, RefreshSession, User
    from app.security import digest

    instant = datetime.now(UTC)
    client = TestClient(app, headers={"Origin": get_settings().frontend_url})
    address = uuid.uuid4().hex + "@example.com"
    body = {"email": address, "display_name": "Expiry", "password": "valid-password"}
    result = client.post("/api/auth/register", json=body)
    access = result.json()["access_token"]
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == address))
        session = db.scalar(
            select(RefreshSession).where(RefreshSession.user_id == user.id)
        )
        session.expires_at = instant - timedelta(seconds=1)
        raw = secrets.token_urlsafe(48)
        db.add(
            PasswordReset(
                user_id=user.id,
                token_hash=digest(raw),
                expires_at=instant - timedelta(seconds=1),
            )
        )
    assert (
        client.post(
            "/api/auth/refresh",
            headers={"X-CSRF-Token": client.cookies.get("gridwatch_csrf")},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/password-reset/confirm",
            json={"token": raw, "password": "new-password"},
        ).status_code
        == 400
    )
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == address))
        user.is_active = False
    assert (
        client.post(
            "/api/auth/login", json={"email": address, "password": "valid-password"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/auth/me", headers={"Authorization": "Bearer " + access}
        ).status_code
        == 401
    )


def test_production_cookie_flags(monkeypatch):
    import uuid

    monkeypatch.setattr(get_settings(), "app_env", "production")
    client = TestClient(app, base_url="https://testserver")
    response = client.post(
        "/api/auth/register",
        json={
            "email": uuid.uuid4().hex + "@example.com",
            "display_name": "Cookies",
            "password": "valid-password",
        },
    )
    assert response.status_code == 201
    cookie = next(
        v
        for v in response.headers.get_list("set-cookie")
        if v.startswith("gridwatch_refresh=")
    )
    for expected in [
        "HttpOnly",
        "Secure",
        "SameSite=strict",
        "Path=/api/auth",
        "Max-Age=604800",
    ]:
        assert expected in cookie


def test_saved_area_ownership_and_normalized_email():
    import uuid
    from datetime import datetime

    from app.db import SessionLocal
    from app.models import Location

    client = TestClient(app)
    suffix = uuid.uuid4().hex

    def signup(email):
        return client.post(
            "/api/auth/register",
            json={
                "email": email,
                "display_name": "Owner",
                "password": "valid-password",
            },
        )

    first = signup("owner-" + suffix + "@example.com")
    assert first.status_code == 201
    assert signup("OWNER-" + suffix.upper() + "@EXAMPLE.COM").status_code == 409
    second = signup("other-" + suffix + "@example.com")
    assert second.status_code == 201
    h1 = {"Authorization": "Bearer " + first.json()["access_token"]}
    h2 = {"Authorization": "Bearer " + second.json()["access_token"]}
    with SessionLocal.begin() as db:
        loc = Location(
            name_bn="পরীক্ষা" + suffix,
            name_en="Ownership " + suffix,
            kind="division",
            slug="owner-" + suffix,
            verification_status="verified",
            source_url="https://example.com/test",
            verified_at=datetime.now(UTC),
        )
        db.add(loc)
        db.flush()
        location_id = str(loc.id)
    for _ in range(2):
        assert (
            client.post("/api/saved-areas/" + location_id, headers=h1).status_code
            == 201
        )
    assert client.get("/api/saved-areas", headers=h2).json()["items"] == []
    assert (
        client.delete("/api/saved-areas/" + location_id, headers=h2).status_code == 204
    )
    assert len(client.get("/api/saved-areas", headers=h1).json()["items"]) == 1


def test_reset_transport_failure_is_generic(monkeypatch):
    import uuid

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import PasswordReset, User

    email = uuid.uuid4().hex + "@example.com"
    client = TestClient(app)
    assert (
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "display_name": "Mail failure",
                "password": "valid-password",
            },
        ).status_code
        == 201
    )

    def unavailable(*args, **kwargs):
        raise OSError("secret mail transport details")

    monkeypatch.setattr("app.auth.smtplib.SMTP", unavailable)
    known = client.post("/api/auth/password-reset/request", json={"email": email})
    unknown = client.post(
        "/api/auth/password-reset/request", json={"email": "missing-" + email}
    )
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert "secret" not in known.text
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert (
            db.scalar(select(PasswordReset).where(PasswordReset.user_id == user.id))
            is None
        )


def test_csrf_required_and_cookie_clearing():
    import uuid

    client = TestClient(app, headers={"Origin": get_settings().frontend_url})
    response = client.post(
        "/api/auth/register",
        json={
            "email": uuid.uuid4().hex + "@example.com",
            "display_name": "CSRF",
            "password": "valid-password",
        },
    )
    assert response.status_code == 201
    assert client.post("/api/auth/refresh").status_code == 403
    assert (
        client.post(
            "/api/auth/logout", headers={"X-CSRF-Token": "incorrect"}
        ).status_code
        == 403
    )
    response = client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": client.cookies.get("gridwatch_csrf")},
    )
    assert response.status_code == 204
    assert not client.cookies.get("gridwatch_refresh")
    assert not client.cookies.get("gridwatch_csrf")
    assert all(
        "Max-Age=0" in v and "SameSite=strict" in v
        for v in response.headers.get_list("set-cookie")
    )


def test_location_pagination_and_filters():
    client = TestClient(app)
    for query in [
        "page=0",
        "page_size=0",
        "page_size=101",
        "kind=police_station",
        "status=official",
    ]:
        assert client.get("/api/locations?" + query).status_code == 422
    first = client.get("/api/locations?page_size=2").json()
    assert first == client.get("/api/locations?page_size=2").json()
    ids = [x["id"] for x in first["items"]]
    second = client.get("/api/locations?page=2&page_size=2").json()
    assert not set(ids) & {x["id"] for x in second["items"]}


def test_concurrent_reset_is_single_use():
    import secrets
    import uuid
    from concurrent.futures import ThreadPoolExecutor
    from datetime import timedelta

    from app.db import SessionLocal
    from app.models import PasswordReset
    from app.security import digest, now

    client = TestClient(app)
    registration = client.post(
        "/api/auth/register",
        json={
            "email": uuid.uuid4().hex + "@example.com",
            "display_name": "Reset concurrency",
            "password": "valid-password",
        },
    )
    assert registration.status_code == 201
    raw = secrets.token_urlsafe(48)
    with SessionLocal.begin() as db:
        db.add(
            PasswordReset(
                user_id=uuid.UUID(registration.json()["user"]["id"]),
                token_hash=digest(raw),
                expires_at=now() + timedelta(minutes=20),
            )
        )

    def reset(_):
        with TestClient(app) as other:
            return other.post(
                "/api/auth/password-reset/confirm",
                json={"token": raw, "password": "replacement-password"},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(reset, range(2))) == [200, 400]
    assert (
        client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer " + registration.json()["access_token"]},
        ).status_code
        == 401
    )
