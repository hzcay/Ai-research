from functools import lru_cache

from fastapi import Header, HTTPException, Request

from src.infrastructure.config.settings import get_settings
from src.utils.logger import setup_logger


@lru_cache()
def init_app_dependencies() -> None:
    settings = get_settings()
    setup_logger(settings.log_level)

def get_settings_dep():
    return get_settings()


async def get_current_user(
    request: Request,
    x_user_id: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
):
    from src.application.container import get_workspace_service
    from src.application.use_cases.manage_auth import AuthService
    from src.infrastructure.database.postgres_repository import async_session_factory

    token = request.cookies.get("research_session")
    if token:
        user = await AuthService(async_session_factory).authenticate(token)
        if user:
            return user
    if x_user_id and x_user_email and x_user_name:
        return await get_workspace_service().ensure_user(x_user_id.strip(), x_user_email.strip(), x_user_name.strip())
    raise HTTPException(status_code=401, detail="Authentication required")
