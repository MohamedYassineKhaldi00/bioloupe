from __future__ import annotations

from fastapi import HTTPException, status


class BioLoupeException(HTTPException):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(status_code=status_code, detail=message)


class DatabaseException(BioLoupeException):
    pass


class VectorDBException(BioLoupeException):
    pass


class StorageException(BioLoupeException):
    pass


class CacheException(BioLoupeException):
    pass


class InvalidCredentials(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("Invalid email or password", status.HTTP_401_UNAUTHORIZED)


class InactiveUser(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("User account is inactive", status.HTTP_403_FORBIDDEN)


class EmailNotVerified(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("Email address not verified", status.HTTP_403_FORBIDDEN)


class TokenExpired(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("Token has expired", status.HTTP_401_UNAUTHORIZED)


class InvalidToken(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("Invalid or malformed token", status.HTTP_401_UNAUTHORIZED)


class InvalidRequest(BioLoupeException):
    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class InvalidOAuthState(BioLoupeException):
    def __init__(self) -> None:
        super().__init__("Invalid or expired OAuth state", status.HTTP_400_BAD_REQUEST)


class PermissionDenied(BioLoupeException):
    def __init__(self, message: str, required_permission: str) -> None:
        super().__init__(
            f"{message}. Required permission: {required_permission}",
            status.HTTP_403_FORBIDDEN
        )


class TeamNotFound(BioLoupeException):
    def __init__(self, team_id: str) -> None:
        super().__init__(f"Team not found: {team_id}", status.HTTP_404_NOT_FOUND)


class SessionNotFound(BioLoupeException):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}", status.HTTP_404_NOT_FOUND)


class NotTeamMember(BioLoupeException):
    def __init__(self, team_id: str, user_id: str) -> None:
        super().__init__(
            f"User {user_id} is not a member of team {team_id}",
            status.HTTP_403_FORBIDDEN
        )


class NotSessionParticipant(BioLoupeException):
    def __init__(self, session_id: str, user_id: str) -> None:
        super().__init__(
            f"User {user_id} is not a participant of session {session_id}",
            status.HTTP_403_FORBIDDEN
        )
