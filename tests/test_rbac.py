# Phase 3 — RBAC tests will live here
import pytest


async def test_admin_routes_not_yet_implemented(client):
    # No routes registered yet; should 404
    resp = await client.get("/admin/users")
    assert resp.status_code == 404
