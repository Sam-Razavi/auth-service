"""Tests for X-Request-ID middleware."""
import uuid


async def test_response_includes_request_id(client):
    resp = await client.get("/health")
    assert "x-request-id" in resp.headers
    # Must be a valid UUID
    uuid.UUID(resp.headers["x-request-id"])


async def test_forwarded_request_id_is_echoed(client):
    custom_id = str(uuid.uuid4())
    resp = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp.headers["x-request-id"] == custom_id


async def test_generated_request_ids_are_unique(client):
    resp1 = await client.get("/health")
    resp2 = await client.get("/health")
    assert resp1.headers["x-request-id"] != resp2.headers["x-request-id"]
