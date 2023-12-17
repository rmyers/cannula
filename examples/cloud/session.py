"""
This is just a simple in memory session for storing our logged in users.

Not really production worthy, just an example of using a session. It is just
a dict. Nothing fancy going on here. It lives in this module so that we can
avoid circular imports.
"""
import logging
import typing
import uuid

import cannula
from cannula.datasource.http import HTTPContext
from graphql import parse
from starlette.responses import RedirectResponse

SESSION = {}
SESSION_COOKE_NAME = "openstack_session_id"
LOG = logging.getLogger(__name__)


class User(typing.NamedTuple):
    catalog: dict = {}
    auth_token: str = ""
    username: str = "anonymous"
    roles: typing.List[str] = []
    session_id: str = ""

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def is_authenticated(self) -> bool:
        return bool(self.auth_token)

    def has_role(self, role):
        return (role in self.roles) or self.is_admin

    def get_service_url(self, service: str, region: str) -> str:
        return self.catalog.get(service, {}).get(region)


def flatten_catalog(catalog: typing.List[dict]) -> dict:
    """Turn the raw service catalog into a simple dict."""
    return {
        service["type"]: {
            endpoint["region"]: endpoint["url"] for endpoint in service["endpoints"]
        }
        for service in catalog
    }


def get_user(session_id: str) -> User:
    user = SESSION.get(session_id)
    if user is not None:
        return user

    # Return an anonymous user object
    return User()


def set_user(
    username: str,
    auth_token: str,
    catalog: typing.List[dict],
    roles: typing.List[dict],
) -> User:
    session_id = str(uuid.uuid4())
    service_catalog = flatten_catalog(catalog)
    user_roles = [role["name"] for role in roles]
    user = User(
        catalog=service_catalog,
        auth_token=auth_token,
        username=username,
        roles=user_roles,
        session_id=session_id,
    )
    SESSION[session_id] = user
    return user


LOGIN_MUTATION = parse(
    """
    mutation token ($username: String!, $password: String!) {
        login(username: $username, password: $password) {
            roles {
                name
            }
            catalog {
                type
                endpoints {
                    region
                    url
                }
            }
            user {
                name
            }
            authToken
        }
    }
"""
)


async def login(
    request: typing.Any,
    username: str,
    password: str,
    api: cannula.API,
) -> bool:
    resp = await api.call(
        LOGIN_MUTATION,
        variables={
            "username": username,
            "password": password,
        },
        request=request,
    )

    if resp.errors:
        LOG.error(f"{resp.errors}")
        raise Exception("Unable to login user")

    LOG.info(f"Auth Response: {resp.data}")
    token = resp.data["login"]
    user = set_user(
        username=token["user"]["name"],
        auth_token=token["authToken"],
        catalog=token["catalog"],
        roles=token["roles"],
    )

    response = RedirectResponse("/dashboard")
    response.set_cookie(SESSION_COOKE_NAME, user.session_id)
    return response


class OpenStackContext(HTTPContext):
    def handle_request(self, request):
        session_id = request.cookies.get(SESSION_COOKE_NAME)
        self.user = get_user(session_id)

        return request


def is_authenticated(request) -> bool:
    session_id = request.cookies.get(SESSION_COOKE_NAME)
    user = get_user(session_id)
    LOG.info(f"{user} {session_id}")
    return user.is_authenticated
