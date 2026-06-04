# Phase 2 — OAuth2 tests will live here
import pytest


async def test_oauth_routes_not_yet_implemented(client):
    # No routes registered yet; both should 404
    resp_gh = await client.get("/oauth/github")
    resp_go = await client.get("/oauth/google")
    assert resp_gh.status_code == 404
    assert resp_go.status_code == 404
