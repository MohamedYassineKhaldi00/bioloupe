import pytest
import json

from app.services.invitation_service import InvitationService, InvitationPayload
from app.core.exceptions import InvitationExpired, InvitationInvalid
from app.models import TeamRole


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.deleted = set()

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.deleted.add(key)
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_create_and_consume_invitation_success(monkeypatch):
    fake = FakeRedis()
    svc = InvitationService(redis=fake)

    payload = InvitationPayload(team_id="t1", email="u@example.com", role=TeamRole.member, invited_by="user-1")
    token = await svc.create_invitation(payload)
    assert isinstance(token, str) and token

    consumed = await svc.consume_invitation(token)
    assert consumed.team_id == payload.team_id
    assert consumed.email == payload.email
    assert consumed.role == payload.role
    assert token and f"team_invite:{token}" in fake.deleted


@pytest.mark.asyncio
async def test_consume_invitation_expired(monkeypatch):
    fake = FakeRedis()
    svc = InvitationService(redis=fake)
    with pytest.raises(InvitationExpired):
        await svc.consume_invitation("missing-token")


@pytest.mark.asyncio
async def test_consume_invitation_invalid_payload(monkeypatch):
    fake = FakeRedis()
    # store invalid JSON
    fake.store["team_invite:bad"] = "not-json"
    svc = InvitationService(redis=fake)
    with pytest.raises(InvitationInvalid):
        await svc.consume_invitation("bad")
