"""
.. _httpdatasource:

HTTP Data Source
================

.. note::

    This requires the http extras to be installed::

        pip install cannula[http]


This is modeled after the apollo http datasource. It uses httpx to preform
async requests to any remote service you wish to query. All GET and HEAD
requests will be memoized so that they are only performed once per
graph resolution.

Example Usage
-------------

::

    @dataclass(kw_only=True)
    class User(UserType):
        id: UUID
        name: str

    class UserAPI(
        HTTPDataSource[User],
        graph_model=User,
        base_url="https://auth.com",
    ):

        async def get_user(self, id) -> User:
            response = await self.get(f"/users/{id}")
            return self.model_from_response(response)

        async def get_users(self) -> list[User]:
            response = await self.get(f"/users")
            return self.model_list_from_response(response)

You can then add this to your context to make it available to your resolvers. It is
best practice to setup a client for all your http datasources to share in order to
handle auth and use the built in connection pool. First add to your context object::

    class Context(cannula.Context):

        def __init__(self, client: httpx.AsyncClient) -> None:
            self.userAPI = UserAPI(client=client)
            self.groupAPI = GroupAPI(client=client)

Next in your graph handler function create a httpx client to use::

    @api.post('/graph')
    async def graph(
        graph_call: Annotated[
            GraphQLExec,
            Depends(GraphQLDepends(cannula_app)),
        ],
        request: Request,
    ) -> ExecutionResponse:
        # Grab the authorization header and create the client
        authorization = request.headers.get('authorization')
        headers = {'authorization': authorization}

        async with httpx.AsyncClient(headers=headers) as client:
            context = Context(client)
            return await graph_call(context=context)

Finally you can now use this datasource in your resolver functions like so::

    async def resolve_person(
        # Using this type hint for the ResolveInfo will make it so that
        # we can inspect the `info` object in our editors and find the `user_api`
        info: cannula.ResolveInfo[Context],
        id: uuid.UUID,
    ) -> UserType | None:
        return await info.context.user_api.get_user(id)

API Reference
-------------
"""

import asyncio
import functools
import logging
import typing
from urllib.parse import urljoin

import httpx
from starlette.datastructures import State
from starlette.requests import Request

from cannula.context import Settings
from cannula.codegen.json_selection import apply_selection
from cannula.datasource import GraphModel, cacheable, expected_fields
from cannula.types import ConnectHTTP, SourceHTTP, HTTPHeaderMapping


LOG = logging.getLogger("cannula.datasource.http")

AnyDict = typing.Dict[typing.Any, typing.Any]
Response = typing.Union[typing.List[AnyDict], AnyDict, httpx.Response]


def model_from_response(
    model: type[GraphModel], response: Response, **kwargs
) -> GraphModel:
    """Return a graph model from a response.

    Use this to return a single model from a http response::

        async def get_user(self, user_id: int) -> User | None:
            response = await self.get(f"/users/{user_id}")
            return self.model_from_response(response)

    Raises:
        AttributeError: if the response object is not a dict

    Args:
        response: a dict response object
        kwargs: optional attributes to set on the GraphModel
    """
    if not isinstance(response, dict):
        raise AttributeError(
            f"Expecting a single object in response but got {type(response).__name__}."
        )

    model_kwargs = response.copy()
    model_kwargs.update(kwargs)
    _expected_fields = expected_fields(model)
    cleaned_kwargs = {
        key: value for key, value in model_kwargs.items() if key in _expected_fields
    }
    obj = model(**cleaned_kwargs)
    return obj


def model_list_from_response(
    model: type[GraphModel], response: Response, **kwargs
) -> typing.List[GraphModel]:
    """Return a list of graph models from a response.

    Use this to return a list of models from a http response::

        async def get_users(self) -> list[User]:
            response = await self.get(f"/users/{user_id}")
            return self.model_from_response(response)

    Raises:
        AttributeError: if the response object is not a list

    Args:
        response: a list of response objects
        kwargs: optional attributes to set on the GraphModel
    """
    if not isinstance(response, list):
        raise AttributeError("Expecting a list in response but got an object.")

    make_model = functools.partial(model_from_response, model, **kwargs)
    return list(map(make_model, response))


class HTTPDatasource(typing.Generic[Settings]):
    """
    HTTP Data Source with Apollo Connect directive support

    This extends the base HTTPDataSource to support configuration via
    Apollo Connect directives, including:
    - Dynamic URL templates
    - Header propagation/injection
    - Request body templating
    - Entity resolution
    - JSON field selection/mapping
    """

    _source_http: SourceHTTP
    # A mapping of requests using the cache_key_for_request. Multiple resolvers
    # could attempt to fetch the same resource, using this we can limit to at
    # most one request per cache key.
    memoized_requests: typing.Dict[str, typing.Awaitable]
    client: httpx.AsyncClient
    _base_url: str
    _headers: typing.List[HTTPHeaderMapping]

    def __init_subclass__(
        cls,
        source: SourceHTTP,
    ) -> None:
        cls._source_http = source
        return super().__init_subclass__()

    def __init__(
        self,
        client: typing.Optional[httpx.AsyncClient] = None,
        request: typing.Optional[Request] = None,
        config: typing.Optional[Settings] = None,
    ):
        """Construct a new HTTPDatasource

        Args:
            client: Optional httpx client to use
        """
        self.client = client or httpx.AsyncClient()
        self.memoized_requests = {}
        # close the client if this instance opened it
        self._should_close_client = client is None
        self._app_config = config or typing.cast(Settings, State())
        self._request = request or Request(scope={"type": "http", "headers": []})
        self._base_url = self._resolve_value(self._source_http.baseURL)
        self._headers = self._source_http.headers

    def __del__(self):  # pragma: no cover
        if self._should_close_client:
            LOG.debug(f"Closing httpx session for {self.__class__.__name__}")
            asyncio.run(self.client.aclose())

    def _render_path_template(
        self, template: str, variables: typing.Dict[str, typing.Any]
    ) -> str:
        """Render a URL path template with variables"""
        # Simple template rendering - replace :varName with values
        path = template
        for name, value in variables.items():
            path = path.replace(f"{{$args.{name}}}", str(value))
        return path

    def _resolve_value(self, value: str) -> str:
        "Handle values that have variables like `$config.secret`"
        if var := value.partition("$config.")[-1]:
            return getattr(self._app_config, var)
        return value

    def _build_headers(
        self,
        header_mappings: typing.List[HTTPHeaderMapping],
    ) -> typing.Dict[str, str]:
        """Build request headers based on header mappings"""
        headers = {}

        for mapping in self._headers + header_mappings:
            if mapping.value:
                # Use static header value
                headers[mapping.name] = self._resolve_value(mapping.value)
            elif mapping.from_header:
                # Propagate header from original request
                if value := self._request.headers.get(mapping.from_header):
                    headers[mapping.name] = value

        return headers

    def _build_url(self, path: str) -> str:
        return urljoin(self._base_url, path)

    def cache_key_for_request(self, request: httpx.Request) -> str:
        if request.method in ["HEAD", "OPTIONS"]:
            # HEAD and OPTIONS are different beasts so we cache them differently
            # all others use the url this way we can clear the 'GET' cache
            # if there is a mutation request to the same URL.
            return f"{request.method}-{request.url}"
        return str(request.url)

    def did_receive_error(self, error: Exception, request: httpx.Request):
        """Handle errors from the remote resource"""
        raise error

    async def did_receive_response(
        self,
        response: httpx.Response,
        request: httpx.Request,
    ) -> Response:
        """Hook to alter the response from the server.

        example::

            async def did_receive_response(
                self, response: httpx.Response, request: Request
            ) -> typing.Any:
                response.raise_for_status()
                return Widget(**response.json())
        """
        response.raise_for_status()
        if request.method == "HEAD":
            return response
        return response.json()

    async def get(self, path: str, **kwargs) -> Response:
        """Convience method to perform a GET :meth:`fetch`

        Args:
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        return await self.fetch("GET", path, **kwargs)

    async def head(self, path: str, **kwargs) -> Response:
        """Convience method to perform a HEAD :meth:`fetch`

        Args:
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        return await self.fetch("HEAD", path, **kwargs)

    async def options(self, path: str, **kwargs) -> Response:
        """Convience method to perform a OPTIONS :meth:`fetch`

        Args:
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        return await self.fetch("OPTIONS", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Response:
        """Convience method to perform a POST :meth:`fetch`

        Args:
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        return await self.fetch("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> Response:
        """Convience method to perform a PATCH :meth:`fetch`

        Args:
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        return await self.fetch("PATCH", path, **kwargs)

    async def put(self, path: str, **kwargs) -> Response:
        """Convience method to perform a PUT :meth:`fetch`

        Args:
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        return await self.fetch("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> Response:
        """Convience method to perform a DELETE :meth:`fetch`

        Args:
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        return await self.fetch("DELETE", path, **kwargs)

    async def fetch(
        self,
        method: str,
        path: str,
        header_mappings: list[HTTPHeaderMapping] | None = None,
        **kwargs,
    ) -> Response:
        """Perform request against the httpx.client

        This method will perform the requests and optionally memoize the
        results so the can be reused by other resolvers. The conveince methods
        just call this with the 'method' set. All the kwargs accepted by the
        httpx client will just pass through.

        Args:
            method: the method to perform
            path: path of the request
            kwargs: these args are passed directly to httpx
        """
        headers = self._build_headers(header_mappings or [])
        url = self._build_url(path)

        request = self.client.build_request(
            method=method, url=url, headers=headers, **kwargs
        )

        cache_key = self.cache_key_for_request(request)

        @cacheable
        async def process_request() -> Response:
            try:
                response = await self.client.send(request)
            except Exception as exc:
                return self.did_receive_error(exc, request)
            else:
                return await self.did_receive_response(response, request)

        if request.method in ["GET", "HEAD", "OPTIONS"]:
            promise = self.memoized_requests.get(cache_key)
            if promise is not None:
                LOG.debug(f"cache found for '{cache_key}'")
                return await promise

            self.memoized_requests[cache_key] = process_request()
            LOG.debug(f"cache set for '{cache_key}'")

            return await self.memoized_requests[cache_key]
        else:
            self.memoized_requests.pop(cache_key, None)
            return await process_request()

    async def execute_operation(
        self,
        connect_http: ConnectHTTP,
        selection: str,
        variables: typing.Optional[dict] = None,
    ) -> Response:
        """
        Execute the HTTP operation configured by connect directives

        Args:
            variables: GraphQL operation variables
            request_headers: Original request headers
        """

        variables = variables or {}

        # Build request configuration
        path = self._render_path_template(connect_http.path, variables)

        # Add body for mutations if configured
        kwargs = {}
        if body_template := connect_http.body:  # pragma: no cover
            LOG.error(body_template)
            # TODO: Implement body template rendering
            kwargs["json"] = variables

        # Execute request using base class

        results = await self.fetch(
            connect_http.method,
            path,
            header_mappings=connect_http.headers,
            **kwargs,
        )
        return apply_selection(results, selection)

    async def get_models(
        self, model: type[GraphModel], response: Response, **kwargs
    ) -> list[GraphModel]:
        return model_list_from_response(model, response, **kwargs)

    async def get_model(
        self, model: type[GraphModel], response: Response, **kwargs
    ) -> GraphModel:
        return model_from_response(model, response, **kwargs)
