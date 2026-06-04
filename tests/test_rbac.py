"""
Phase 3 — RBAC tests.

The `roles` fixture seeds admin/user/moderator into the test DB.
Admin users are created by registering via the API then assigning a
role directly through the shared `db` session before logging in.
"""
import uuid

import pytest
from sqlalchemy import select

from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_login(client, email="u@example.com", password="pass1234"):
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _make_admin(db, email: str, roles: dict) -> None:
    """Assign the admin role to an existing user directly via the test session."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.roles = [roles["admin"]]
    await db.commit()


# ---------------------------------------------------------------------------
# /auth/me — roles field
# ---------------------------------------------------------------------------

async def test_me_includes_empty_roles_for_new_user(client):
    token = await _register_login(client, "norole@example.com")
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["roles"] == []


async def test_me_includes_assigned_roles(client, db, roles):
    token = await _register_login(client, "withrole@example.com")
    await _make_admin(db, "withrole@example.com", roles)
    # Re-login to get a fresh token (user object re-loaded with roles)
    resp = await client.post("/auth/login", json={"email": "withrole@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert "admin" in me.json()["roles"]


# ---------------------------------------------------------------------------
# Admin gate — unauthenticated and unprivileged access
# ---------------------------------------------------------------------------

async def test_admin_users_requires_auth(client):
    resp = await client.get("/admin/users")
    assert resp.status_code == 403  # HTTPBearer returns 403 with no header


async def test_admin_users_requires_admin_role(client, roles):
    token = await _register_login(client, "plain@example.com")
    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]


async def test_moderator_cannot_access_admin_routes(client, db, roles):
    token = await _register_login(client, "mod@example.com")
    result = await db.execute(select(User).where(User.email == "mod@example.com"))
    user = result.scalar_one()
    user.roles = [roles["moderator"]]
    await db.commit()

    resp = await client.post("/auth/login", json={"email": "mod@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

async def test_admin_can_list_users(client, db, roles):
    await _register_login(client, "admin@example.com")
    await _make_admin(db, "admin@example.com", roles)
    await client.post("/auth/register", json={"email": "other@example.com", "password": "pass1234"})

    resp = await client.post("/auth/login", json={"email": "admin@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "admin@example.com" in emails
    assert "other@example.com" in emails


async def test_admin_list_users_skip_limit(client, db, roles):
    await _register_login(client, "admin2@example.com")
    await _make_admin(db, "admin2@example.com", roles)
    for i in range(3):
        await client.post("/auth/register", json={"email": f"user{i}@example.com", "password": "pass1234"})

    resp = await client.post("/auth/login", json={"email": "admin2@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    resp = await client.get("/admin/users?skip=0&limit=2", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# GET /admin/users/{id}
# ---------------------------------------------------------------------------

async def test_admin_get_user_by_id(client, db, roles):
    await _register_login(client, "admin3@example.com")
    await _make_admin(db, "admin3@example.com", roles)
    await client.post("/auth/register", json={"email": "target@example.com", "password": "pass1234"})

    resp = await client.post("/auth/login", json={"email": "admin3@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    list_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    target = next(u for u in list_resp.json() if u["email"] == "target@example.com")

    resp = await client.get(f"/admin/users/{target['id']}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "target@example.com"


async def test_admin_get_nonexistent_user_returns_404(client, db, roles):
    await _register_login(client, "admin4@example.com")
    await _make_admin(db, "admin4@example.com", roles)
    resp = await client.post("/auth/login", json={"email": "admin4@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    resp = await client.get(
        f"/admin/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /admin/users/{id}/roles
# ---------------------------------------------------------------------------

async def test_admin_can_assign_roles(client, db, roles):
    await _register_login(client, "admin5@example.com")
    await _make_admin(db, "admin5@example.com", roles)
    await client.post("/auth/register", json={"email": "promoted@example.com", "password": "pass1234"})

    resp = await client.post("/auth/login", json={"email": "admin5@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    list_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    target = next(u for u in list_resp.json() if u["email"] == "promoted@example.com")

    resp = await client.put(
        f"/admin/users/{target['id']}/roles",
        json={"roles": ["moderator"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["roles"] == ["moderator"]


async def test_assign_unknown_role_returns_400(client, db, roles):
    await _register_login(client, "admin6@example.com")
    await _make_admin(db, "admin6@example.com", roles)

    resp = await client.post("/auth/login", json={"email": "admin6@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    list_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    target = list_resp.json()[0]

    resp = await client.put(
        f"/admin/users/{target['id']}/roles",
        json={"roles": ["superuser"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "superuser" in resp.json()["detail"]


async def test_assign_roles_replaces_all_existing(client, db, roles):
    """Assigning a new role set fully replaces the previous one."""
    await _register_login(client, "admin7@example.com")
    await _make_admin(db, "admin7@example.com", roles)
    await client.post("/auth/register", json={"email": "swap@example.com", "password": "pass1234"})

    resp = await client.post("/auth/login", json={"email": "admin7@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    list_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    target = next(u for u in list_resp.json() if u["email"] == "swap@example.com")

    # First assignment
    await client.put(
        f"/admin/users/{target['id']}/roles",
        json={"roles": ["user"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Second assignment should replace
    resp = await client.put(
        f"/admin/users/{target['id']}/roles",
        json={"roles": ["moderator"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["roles"] == ["moderator"]


async def test_assign_empty_roles_clears_all(client, db, roles):
    await _register_login(client, "admin8@example.com")
    await _make_admin(db, "admin8@example.com", roles)
    await client.post("/auth/register", json={"email": "clear@example.com", "password": "pass1234"})

    resp = await client.post("/auth/login", json={"email": "admin8@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    list_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    target = next(u for u in list_resp.json() if u["email"] == "clear@example.com")

    resp = await client.put(
        f"/admin/users/{target['id']}/roles",
        json={"roles": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["roles"] == []


# ---------------------------------------------------------------------------
# DELETE /admin/users/{id}
# ---------------------------------------------------------------------------

async def test_admin_can_deactivate_user(client, db, roles):
    await _register_login(client, "admin9@example.com")
    await _make_admin(db, "admin9@example.com", roles)
    await client.post("/auth/register", json={"email": "bye@example.com", "password": "pass1234"})

    resp = await client.post("/auth/login", json={"email": "admin9@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    list_resp = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    target = next(u for u in list_resp.json() if u["email"] == "bye@example.com")

    del_resp = await client.delete(
        f"/admin/users/{target['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204

    # Deactivated user cannot log in
    login_resp = await client.post(
        "/auth/login", json={"email": "bye@example.com", "password": "pass1234"}
    )
    assert login_resp.status_code == 401


async def test_deactivate_nonexistent_user_returns_404(client, db, roles):
    await _register_login(client, "admin10@example.com")
    await _make_admin(db, "admin10@example.com", roles)
    resp = await client.post("/auth/login", json={"email": "admin10@example.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    resp = await client.delete(
        f"/admin/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
