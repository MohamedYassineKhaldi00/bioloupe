from types import SimpleNamespace


def make_fake_team_service():
    class FakeTeam:
        def __init__(self, id, name, description, created_by_id=None):
            self.id = id
            self.name = name
            self.description = description
            self.created_by_id = created_by_id
            # lightweight timestamps expected by TeamResponse
            self.created_at = "2025-01-01T00:00:00Z"
            self.updated_at = "2025-01-01T00:00:00Z"

    class FakeMember(SimpleNamespace):
        pass

    class FakeTeamService:
        def __init__(self, db):
            # in-memory store
            self._teams = {"team-1": FakeTeam("team-1", "T1", "desc", "user-1")}

        async def create_team(self, name, description, user_id):
            return FakeTeam("team-1", name, description, created_by_id=user_id)

        async def list_teams_for_user(self, user_id):
            return [{"id": "team-1", "name": "T1", "description": "desc", "role": "owner", "member_count": 1}]

        async def get_team(self, team_id):
            return self._teams.get(team_id)

        async def update_team(self, team_id, name, description):
            t = self._teams.get(team_id)
            if name is not None:
                t.name = name
            if description is not None:
                t.description = description
            return t

        async def delete_team(self, team_id):
            self._teams.pop(team_id, None)

        async def add_member(self, team_id, user_id, role):
            return FakeMember(id="mem-1", team_id=team_id, user_id=user_id, role=role, joined_at="2025-01-01T00:00:00Z")

        async def list_members(self, team_id):
            return [{"id": "mem-1", "team_id": team_id, "user_id": "user-2", "role": "member", "joined_at": "2025-01-01T00:00:00Z"}]

        async def update_member_role(self, team_id, user_id, role):
            return FakeMember(id="mem-1", team_id=team_id, user_id=user_id, role=role, joined_at="2025-01-01T00:00:00Z")

        async def remove_member(self, team_id, user_id):
            return None

    return FakeTeamService


def test_create_team_success(client, monkeypatch):
    Fake = make_fake_team_service()

    # Patch TeamService used inside the endpoint module and make role checks return owner
    monkeypatch.setattr("app.api.v1.endpoints.teams.TeamService", Fake)
    monkeypatch.setattr("app.api.v1.endpoints.teams.team_role_required", lambda roles: (lambda *a, **k: SimpleNamespace(role="owner")))
    # ensure low-level permission helper does not hit the DB during tests
    async def _no_team_perm(*a, **k):
        return SimpleNamespace(role="owner")
    monkeypatch.setattr("app.api.dependencies.permissions.require_team_permission", _no_team_perm)

    resp = client.post("/api/v1/teams", json={"name": "Test Team", "description": "A team"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Team"
    assert data["id"] == "team-1"


def test_list_teams(client, monkeypatch):
    Fake = make_fake_team_service()
    monkeypatch.setattr("app.api.v1.endpoints.teams.TeamService", Fake)
    # disable permission DB calls for this test
    async def _no_team_perm(*a, **k):
        return SimpleNamespace(role="owner")
    monkeypatch.setattr("app.api.dependencies.permissions.require_team_permission", _no_team_perm)

    resp = client.get("/api/v1/teams")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data and data[0]["name"] == "T1"


def test_add_and_list_members(client, monkeypatch):
    Fake = make_fake_team_service()
    monkeypatch.setattr("app.api.v1.endpoints.teams.TeamService", Fake)
    monkeypatch.setattr("app.api.v1.endpoints.teams.team_role_required", lambda roles: (lambda *a, **k: SimpleNamespace(role="owner")))
    # ensure permission helper doesn't hit the DB
    async def _no_team_perm(*a, **k):
        return SimpleNamespace(role="owner")
    monkeypatch.setattr("app.api.dependencies.permissions.require_team_permission", _no_team_perm)

    # add member
    resp = client.post("/api/v1/teams/team-1/members", json={"user_id": "user-2", "role": "member"})
    assert resp.status_code == 200
    member = resp.json()
    assert member["user_id"] == "user-2"
    assert member["role"] == "member"

    # list members
    resp = client.get("/api/v1/teams/team-1/members")
    assert resp.status_code == 200
    members = resp.json()
    assert isinstance(members, list)
    assert members and members[0]["user_id"] == "user-2"
