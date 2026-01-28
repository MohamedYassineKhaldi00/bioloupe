from types import SimpleNamespace


def test_create_invitation_endpoint(client, monkeypatch):
    # Patch permission and InvitationService
    async def _no_team_perm(*a, **k):
        return None

    monkeypatch.setattr("app.api.v1.endpoints.teams.require_team_permission", _no_team_perm)

    class FakeInvitationService:
        async def create_invitation(self, payload):
            return "token-123"

    monkeypatch.setattr("app.api.v1.endpoints.teams.InvitationService", lambda: FakeInvitationService())

    resp = client.post("/api/v1/teams/team-1/invitations", json={"email": "foo@example.com", "role": "member"})
    assert resp.status_code == 200
    assert resp.json().get("token") == "token-123"


def test_accept_invitation_endpoint(client, monkeypatch):
    # Patch get_current_active_user to have email matching invitation
    async def _get_current_user():
        return SimpleNamespace(id="user-1", email="test@example.com")

    monkeypatch.setattr("app.api.v1.endpoints.teams.get_current_active_user", _get_current_user)

    # Fake InvitationService.consume_invitation returns payload
    class FakeInvitePayload(SimpleNamespace):
        pass

    class FakeInvitationService:
        async def consume_invitation(self, token):
            return FakeInvitePayload(team_id="team-1", email="test@example.com", role="member", invited_by="user-1")

    monkeypatch.setattr("app.api.v1.endpoints.teams.InvitationService", lambda: FakeInvitationService())

    # Patch TeamService.add_member to confirm it's called
    added = {}

    class FakeTeamService:
        def __init__(self, db):
            pass

        async def add_member(self, team_id, user_id, role):
            added["team_id"] = team_id
            added["user_id"] = user_id
            added["role"] = role
            return SimpleNamespace(id="mem-1", team_id=team_id, user_id=user_id, role=role)

    monkeypatch.setattr("app.api.v1.endpoints.teams.TeamService", FakeTeamService)

    resp = client.post("/api/v1/teams/invitations/token-abc/accept")
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    assert added.get("team_id") == "team-1"
