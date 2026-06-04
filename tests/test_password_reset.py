# Phase 4 — password reset tests will live here
import pytest


async def test_forgot_password_stub(client):
    resp = await client.post("/auth/forgot-password")
    assert resp.status_code == 501


async def test_reset_password_stub(client):
    resp = await client.post("/auth/reset-password")
    assert resp.status_code == 501
