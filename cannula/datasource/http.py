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

import httpx

from cannula.datasource import GraphModel, cacheable, expected_fields

LOG = logging.getLogger("cannula.datasource.http")

AnyDict = typing.Dict[typing.Any, typing.Any]
Response = typing.Union[typing.List[AnyDict], AnyDict, httpx.Response]


class HTTPDataSource(typing.Generic[GraphModel]):
    """HTTP Data Source

    Class Properties:

    * `graph_model`: This is the object type your schema is expecting to respond with.
    * `base_url`: Optional base_url to apply to all requests
    * `timeout`: Default timeout in seconds for requests (5 seconds)

    This uses a __init_subclass__ which you can use to create a subclass like::

        class UserAPI(
            HTTPDataSource[User],  # Sets the type hints for the 'Response' object
            graph_model=User,
            base_url="https://auth.com",
            timeout=10,
        ): ...

    Then when you construct a instance to use with an optional client::

        client = httpx.AsyncClient(headers={'Authorization': 'Bearer my-token'})
        my_datasource = UserAPI(client)

    Args:
        client: Optional httpx client to use for requests.

    After the response is returned you can use :meth:`model_from_response` or
    :meth:`model_list_from_response` to return graph models for the resolvers to use.
    This is especially useful if these models have computed functions on them.
    """

    _graph_model: type[GraphModel]
    _expected_fields: set[str]
    # The base url of this resource
    _base_url: typing.Optional[httpx.URL]
    # A mapping of requests using the cache_key_for_request. Multiple resolvers
    # could attempt to fetch the same resource, using this we can limit to at
    # most one request per cache key.
    memoized_requests: typing.Dict[str, typing.Awaitable]

    # Timeout for an individual request in seconds.
    _timeout: typing.Optional[httpx.Timeout]

    def __init_subclass__(
        cls,
        graph_model: type[GraphModel],
        base_url: typing.Optional[httpx.URL] = None,
        timeout: typing.Optional[httpx.Timeout] = None,
    ) -> None:
        cls._graph_model = graph_model
        cls._expected_fields = expected_fields(graph_model)
        cls._base_url = base_url
        cls._timeout = timeout
        return super().__init_subclass__()

    def __init__(
        self,
        client: typing.Optional[httpx.AsyncClient] = None,
    ):
        """Construct a new HTTPDatasource

        Args:
            client: Optional httpx client to use
        """
        self.client = client or httpx.AsyncClient()
        self.memoized_requests = {}
        # close the client if this instance opened it
        self._should_close_client = client is None
        # Set the base url on the client only if it is set
        if self._base_url:
            self.client.base_url = self._base_url
        # Set default timeout on client only if it is set
        if self._timeout:
            self.client.timeout = self._timeout

    def __del__(self):  # pragma: no cover
        if self._should_close_client:
            LOG.debug(f"Closing httpx session for {self.__class__.__name__}")
            asyncio.run(self.client.aclose())

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

    async def fetch(self, method: str, path: str, **kwargs) -> Response:
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
        request = self.client.build_request(method=method, url=path, **kwargs)

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

    def model_from_response(self, response: Response, **kwargs) -> GraphModel:
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

        make_model = functools.partial(self.model_from_response, **kwargs)
        return list(map(make_model, response))
