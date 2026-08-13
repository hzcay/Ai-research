from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.application.use_cases.manage_auth import AuthError, AuthService
from src.infrastructure.database.postgres_repository import async_session_factory

router = APIRouter()
COOKIE_NAME = "research_session"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    display_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str


def service() -> AuthService:
    return AuthService(async_session_factory)


def set_session(response: Response, token: str) -> None:
    response.set_cookie(COOKIE_NAME, token, max_age=30 * 24 * 3600, httponly=True, samesite="lax", secure=False, path="/")


@router.post("/register")
async def register(req: RegisterRequest, response: Response):
    try:
        user, token = await service().register(req.email, req.display_name, req.password)
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    set_session(response, token)
    return user


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    try:
        user, token = await service().login(req.email, req.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    set_session(response, token)
    return user


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await service().logout(token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "logged_out"}
