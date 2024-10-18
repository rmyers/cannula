import typing

from fastapi import Request, APIRouter, Form, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .database import User
from .repository import UserRepository, SESSION
from .config import config

SESSION_COOKIE = "session_id"

auth_router = APIRouter(prefix="/auth")


async def check_session(session_id: str) -> typing.Optional[User]:
    return SESSION.get(session_id)


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: typing.Callable):
        session_id = request.cookies.get(SESSION_COOKIE)
        request.scope["user"] = await check_session(str(session_id))
        return await call_next(request)


@auth_router.post("/login")
async def login(
    email: typing.Annotated[str, Form()], password: typing.Annotated[str, Form()]
):
    async with config.session() as db_session:
        users = UserRepository(db_session)
        session = await users.signin(email=email, password=password)
        response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(SESSION_COOKIE, str(session))
        return response


@auth_router.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(SESSION_COOKIE, "")
    return response
