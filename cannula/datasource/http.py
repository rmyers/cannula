"""
.. _httpdatasource:

HTTP Data Source
================

.. note::

    This requires the http extras to be installed::

        pip install cannula[http]

"""

import asyncio
import logging
import typing

import httpx

from cannula.datasource import GraphModel, cacheable, expected_fields

LOG = logging.getLogger("cannula.datasource.http")

AnyDict = typing.Dict[typing.Any, typing.Any]
Response = typing.Union[typing.List[AnyDict], AnyDict]


class Request(typing.NamedTuple):
    url: str
    method: str
    body: typing.Any = None
    headers: typing.Dict = {}


class HTTPDataSource(typing.Generic[GraphModel]):
    """
    HTTP Data Source

    This is modeled after the apollo http datasource. It uses httpx to preform
    async requests to any remote service you wish to query. All GET and HEAD
    requests will be memoized so that they are only performed once per
    graph resolution.

    Properties:

    * `graph_model`: This is the object type your schema is expecting to respond with.
    * `base_url`: Optional base_url to apply to all requests
    * `timeout`: Default timeout in seconds for requests (5 seconds)

    Example::

        @dataclass(kw_only=True)
        class User(UserTypeBase):
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
    """

    _graph_model: type[GraphModel]
    _expected_fields: set[str]
    # The base url of this resource
    base_url: typing.Optional[str] = None
    # A mapping of requests using the cache_key_for_request. Multiple resolvers
    # could attempt to fetch the same resource, using this we can limit to at
    # most one request per cache key.
    memoized_requests: typing.Dict[str, typing.Awaitable]

    # Timeout for an individual request in seconds.
    timeout: int = 5

    def __init_subclass__(
        cls,
        graph_model: type[GraphModel],
        base_url: typing.Optional[str] = None,
        timeout: int = 5,
    ) -> None:
        cls._graph_model = graph_model
        cls._expected_fields = expected_fields(graph_model)
        cls.base_url = base_url
        cls.timeout = timeout
        return super().__init_subclass__()

    def __init__(
        self,
        client: typing.Optional[httpx.AsyncClient] = None,
    ):
        self.client = client or httpx.AsyncClient()
        # close the client if this instance opened it
        self._should_close_client = client is None
        self.memoized_requests = {}

    def __del__(self):  # pragma: no cover
        if self._should_close_client:
            LOG.debug(f"Closing httpx session for {self.__class__.__name__}")
            asyncio.ensure_future(self.client.aclose())

    def will_send_request(self, request: Request) -> Request:
        """Hook for subclasses to modify the request before it is sent.

        For example setting Authorization headers::

            def will_send_request(self, request):
                request.headers = self.request.headers
                return request
        """
        return request

    def cache_key_for_request(self, request: Request) -> str:
        return request.url

    def get_request_url(self, path: str) -> str:
        if path.startswith(("https://", "http://")):
            return path

        if self.base_url is not None:
            if path.startswith("/"):
                path = path[1:]

            if self.base_url.endswith("/"):
                return f"{self.base_url}{path}"

            return f"{self.base_url}/{path}"

        return path

    def did_receive_error(self, error: Exception, request: Request):
        """Handle errors from the remote resource"""
        raise error

    async def did_receive_response(
        self,
        response: httpx.Response,
        request: Request,
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
        return response.json()

    async def get(self, path: str) -> Response:
        """Preform a GET request

        :param path: path of the request
        """
        return await self.fetch("GET", path)

    async def post(self, path: str, body: typing.Any) -> Response:
        """Preform a POST request

        :param path: path of the request
        :param body: body of the request
        """
        return await self.fetch("POST", path, body)

    async def patch(self, path: str, body: typing.Any) -> Response:
        """Preform a PATCH request

        :param path: path of the request
        :param body: body of the request
        """
        return await self.fetch("PATCH", path, body)

    async def put(self, path: str, body: typing.Any) -> Response:
        """Preform a PUT request

        :param path: path of the request
        :param body: body of the request
        """
        return await self.fetch("PUT", path, body)

    async def delete(self, path: str) -> Response:
        """Preform a DELETE request

        :param path: path of the request
        """
        return await self.fetch("DELETE", path)

    async def fetch(self, method: str, path: str, body: typing.Any = None) -> Response:
        url = self.get_request_url(path)

        request = Request(url, method, body)

        request = self.will_send_request(request)

        cache_key = self.cache_key_for_request(request)

        @cacheable
        async def process_request() -> Response:
            try:
                response = await self.client.request(
                    request.method,
                    request.url,
                    json=request.body,
                    headers=request.headers,
                    timeout=self.timeout,
                )
            except Exception as exc:
                return self.did_receive_error(exc, request)
            else:
                return await self.did_receive_response(response, request)

        if request.method == "GET":
            promise = self.memoized_requests.get(cache_key)
            if promise is not None:
                LOG.debug(f"cache found for GET '{cache_key}'")
                return await promise

            self.memoized_requests[cache_key] = process_request()
            LOG.debug(f"cache set for GET '{cache_key}'")

            return await self.memoized_requests[cache_key]
        else:
            self.memoized_requests.pop(cache_key, None)
            return await process_request()

    def model_from_response(self, response: AnyDict, **kwargs) -> GraphModel:
        model_kwargs = response.copy()
        model_kwargs.update(kwargs)
        cleaned_kwargs = {
            key: value
            for key, value in model_kwargs.items()
            if key in self._expected_fields
        }
        obj = self._graph_model(**cleaned_kwargs)
        return obj

    def model_list_from_response(
        self, response: Response, **kwargs
    ) -> typing.List[GraphModel]:
        return list(map(self.model_from_response, response))
