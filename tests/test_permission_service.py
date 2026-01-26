from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.permission_service import PermissionService
from src.app.models.team import Team, TeamMember, TeamRole
from src.app.models.session import Session, SessionParticipant, SessionPermission
from src.app.models.user import User
from src.app.core.exceptions import (
    TeamNotFound,
    SessionNotFound,
    NotTeamMember,
    PermissionDenied
)


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def permission_service(mock_db: AsyncMock) -> PermissionService:
    return PermissionService(mock_db)


@pytest.fixture
def sample_user() -> User:
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def sample_team() -> Team:
    team = Mock(spec=Team)
    team.id = uuid.uuid4()
    return team


@pytest.fixture
def sample_session(sample_team: Team) -> Session:
    session = Mock(spec=Session)
    session.id = uuid.uuid4()
    session.team_id = sample_team.id
    session.is_deleted = False
    return session


class TestTeamPermissions:
    @pytest.mark.asyncio
    async def test_get_team_membership_success(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_team: Team
    ) -> None:
        membership = Mock(spec=TeamMember)
        membership.role = TeamRole.member
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = membership
        mock_db.execute.return_value = mock_result

        result = await permission_service.get_team_membership(
            sample_team.id, sample_user.id
        )

        assert result == membership
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_team_membership_not_member(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_team: Team
    ) -> None:
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotTeamMember):
            await permission_service.verify_team_membership(
                sample_team.id, sample_user.id
            )

    @pytest.mark.asyncio
    async def test_verify_team_permission_insufficient_role(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_team: Team
    ) -> None:
        membership = Mock(spec=TeamMember)
        membership.role = TeamRole.viewer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = membership
        mock_db.execute.return_value = mock_result

        with pytest.raises(PermissionDenied):
            await permission_service.verify_team_permission(
                sample_team.id, sample_user.id, [TeamRole.admin, TeamRole.owner]
            )

    @pytest.mark.asyncio
    async def test_verify_team_permission_sufficient_role(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_team: Team
    ) -> None:
        membership = Mock(spec=TeamMember)
        membership.role = TeamRole.admin
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = membership
        mock_db.execute.return_value = mock_result

        result = await permission_service.verify_team_permission(
            sample_team.id, sample_user.id, [TeamRole.admin, TeamRole.owner]
        )

        assert result == membership

    def test_check_team_role_hierarchy(
        self, permission_service: PermissionService
    ) -> None:
        assert permission_service.check_team_role_hierarchy(
            TeamRole.owner, TeamRole.admin
        )
        assert permission_service.check_team_role_hierarchy(
            TeamRole.admin, TeamRole.member
        )
        assert not permission_service.check_team_role_hierarchy(
            TeamRole.viewer, TeamRole.member
        )


class TestSessionPermissions:
    @pytest.mark.asyncio
    async def test_get_session_participant_exists(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_session: Session
    ) -> None:
        participant = Mock(spec=SessionParticipant)
        participant.permission = SessionPermission.write
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = participant
        mock_db.execute.return_value = mock_result

        result = await permission_service.get_session_participant(
            sample_session.id, sample_user.id
        )

        assert result == participant

    @pytest.mark.asyncio
    async def test_resolve_session_permission_direct_participant(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_session: Session
    ) -> None:
        participant = Mock(spec=SessionParticipant)
        participant.permission = SessionPermission.admin
        mock_result_session = AsyncMock()
        mock_result_session.scalar_one_or_none.return_value = sample_session
        mock_result_participant = AsyncMock()
        mock_result_participant.scalar_one_or_none.return_value = participant

        mock_db.execute.side_effect = [
            mock_result_session, mock_result_participant
        ]

        session, permission = await permission_service.resolve_session_permission(
            sample_session.id, sample_user.id
        )

        assert session == sample_session
        assert permission == SessionPermission.admin

    @pytest.mark.asyncio
    async def test_resolve_session_permission_via_team_membership(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_session: Session
    ) -> None:
        team_member = Mock(spec=TeamMember)
        team_member.role = TeamRole.admin
        mock_result_session = AsyncMock()
        mock_result_session.scalar_one_or_none.return_value = sample_session
        mock_result_participant = AsyncMock()
        mock_result_participant.scalar_one_or_none.return_value = None
        mock_result_team = AsyncMock()
        mock_result_team.scalar_one_or_none.return_value = team_member

        mock_db.execute.side_effect = [
            mock_result_session, mock_result_participant, mock_result_team
        ]

        session, permission = await permission_service.resolve_session_permission(
            sample_session.id, sample_user.id
        )

        assert session == sample_session
        assert permission == SessionPermission.admin

    @pytest.mark.asyncio
    async def test_resolve_session_permission_no_access(
        self, permission_service: PermissionService, mock_db: AsyncMock,
        sample_user: User, sample_session: Session
    ) -> None:
        mock_result_session = AsyncMock()
        mock_result_session.scalar_one_or_none.return_value = sample_session
        mock_result_participant = AsyncMock()
        mock_result_participant.scalar_one_or_none.return_value = None
        mock_result_team = AsyncMock()
        mock_result_team.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [
            mock_result_session, mock_result_participant, mock_result_team
        ]

        with pytest.raises(PermissionDenied):
            await permission_service.resolve_session_permission(
                sample_session.id, sample_user.id
            )

    def test_map_team_role_to_session_permission(
        self, permission_service: PermissionService
    ) -> None:
        assert (
            permission_service._map_team_role_to_session_permission(TeamRole.owner)
            == SessionPermission.admin
        )
        assert (
            permission_service._map_team_role_to_session_permission(TeamRole.admin)
            == SessionPermission.admin
        )
        assert (
            permission_service._map_team_role_to_session_permission(TeamRole.member)
            == SessionPermission.write
        )
        assert (
            permission_service._map_team_role_to_session_permission(TeamRole.viewer)
            == SessionPermission.read
        )

    def test_check_session_permission_hierarchy(
        self, permission_service: PermissionService
    ) -> None:
        assert permission_service.check_session_permission_hierarchy(
            SessionPermission.admin, SessionPermission.write
        )
        assert permission_service.check_session_permission_hierarchy(
            SessionPermission.write, SessionPermission.read
        )
        assert not permission_service.check_session_permission_hierarchy(
            SessionPermission.read, SessionPermission.write
        )
