from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select

from src.infrastructure.database.models import User, UserSession


class AuthError(ValueError):
    pass


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _password_valid(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        _, salt, expected = encoded.split("$", 2)
        actual = _password_hash(password, base64.urlsafe_b64decode(salt)).split("$", 2)[2]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, session_factory) -> None:
        self._sessions = session_factory

    async def register(self, email: str, display_name: str, password: str) -> tuple[dict, str]:
        email = email.strip().lower()
        display_name = display_name.strip()
        if len(password) < 8:
            raise AuthError("Password must contain at least 8 characters")
        async with self._sessions() as session:
            if await session.scalar(select(User).where(User.email == email)):
                raise AuthError("An account with this email already exists")
            user = User(id=str(uuid4()), email=email, display_name=display_name, password_hash=_password_hash(password))
            session.add(user)
            token = await self._create_session(session, user.id)
            await session.commit()
            return self._user(user), token

    async def login(self, email: str, password: str) -> tuple[dict, str]:
        async with self._sessions() as session:
            user = await session.scalar(select(User).where(User.email == email.strip().lower()))
            if not user or not user.is_active or not _password_valid(password, user.password_hash):
                raise AuthError("Invalid email or password")
            token = await self._create_session(session, user.id)
            await session.commit()
            return self._user(user), token

    async def authenticate(self, token: str) -> dict | None:
        async with self._sessions() as session:
            auth_session = await session.scalar(select(UserSession).where(UserSession.token_hash == _token_hash(token)))
            if not auth_session or auth_session.expires_at <= datetime.utcnow():
                return None
            user = await session.get(User, auth_session.user_id)
            return self._user(user) if user and user.is_active else None

    async def logout(self, token: str) -> None:
        async with self._sessions() as session:
            await session.execute(delete(UserSession).where(UserSession.token_hash == _token_hash(token)))
            await session.commit()

    async def _create_session(self, session, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        session.add(UserSession(id=str(uuid4()), user_id=user_id, token_hash=_token_hash(token), expires_at=datetime.utcnow() + timedelta(days=30)))
        return token

    @staticmethod
    def _user(user: User) -> dict:
        return {"id": user.id, "email": user.email, "display_name": user.display_name}
