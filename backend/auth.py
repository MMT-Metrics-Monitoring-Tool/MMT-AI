from dataclasses import dataclass

import datetime
import jwt
import os


@dataclass(frozen=True)
class Principal:
    """The authenticated MMT user making a request."""
    user_id: str
    project_ids: frozenset[int]
    name: str | None = None

    def can_access(self, project_id: int) -> bool:
        return project_id in self.project_ids


class AuthError(Exception):
    def __init__(self, message: str, expired: bool = False):
        super().__init__(message)
        self.expired = expired


@dataclass(frozen=True)
class Authenticator:
    """Verifies the tokens MMT issues for the chatbot.

    Token contract (JWT signed by MMT with the shared JWT_SECRET_KEY, algorithm JWT_ALGORITHM):
        sub          MMT user ID (string)
        project_ids  IDs of the projects the user may access (list of integers)
        name         Display name (optional)
        exp          Expiry time (required)
    """
    secret_key: str
    algorithm: str
    dev_mode: bool = False
    dev_project_ids: frozenset[int] = frozenset({1})
    dev_token_ttl_seconds: int = 1800

    def verify(self, token: str | None) -> Principal:
        if not token:
            raise AuthError("Missing token")
        if token.lower().startswith("bearer "):
            token = token[7:]
        try:
            claims = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], options={"require": ["exp", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise AuthError("Token expired", expired=True)
        except jwt.InvalidTokenError as exc:
            raise AuthError(f"Invalid token: {exc}")

        try:
            project_ids = frozenset(int(pid) for pid in claims.get("project_ids", []))
        except (TypeError, ValueError):
            raise AuthError("Invalid token: project_ids must be a list of integers")
        return Principal(user_id=str(claims["sub"]), project_ids=project_ids, name=claims.get("name"))

    def issue_dev_token(self) -> str:
        """Issues a token for local development without MMT. Only available when AUTH_DEV_MODE is enabled."""
        if not self.dev_mode:
            raise AuthError("Development tokens are disabled")
        payload = {
            "sub": "dev-user",
            "name": "Developer",
            "project_ids": sorted(self.dev_project_ids),
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=self.dev_token_ttl_seconds),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


def build_authenticator() -> Authenticator:
    """
    Factory: builds the authenticator from the environment.
    """
    return Authenticator(
        secret_key=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        dev_mode=os.getenv("AUTH_DEV_MODE", "false").lower() in ("1", "true", "yes", "on"),
        dev_project_ids=frozenset(int(pid) for pid in os.getenv("DEV_PROJECT_IDS", "1").split(",") if pid.strip()),
    )
