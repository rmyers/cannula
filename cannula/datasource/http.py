"""
.. _httpdatasource:

HTTP Data Source
================

First install the extras::

    pip install cannula[http]
"""

import asyncio
import logging
import types
import typing

import httpx

LOG = logging.getLogger("cannula.datasource.http")


# solves the issue of `cannot reuse already awaited coroutine`
def cacheable(f):
    def wrapped(*args, **kwargs):
        r = f(*args, **kwargs)
        return asyncio.ensure_future(r)

    return wrapped


class Request(typing.NamedTuple):
    url: str
    method: str
    body: typing.Any = None
    headers: typing.Dict = {}


class HTTPDataSource:
    """
    HTTP Data Source

    This is modeled after the apollo http datasource. It uses httpx to preform
    async requests to any remote service you wish to query.

    Properties:

    * `base_url`: Optional base_url to apply to all requests
    * `timeout`: Default timeout in seconds for requests (5 seconds)
    * `resource_name`: Optional name to use for `__typename` in responses.
    """

    # The base url of this resource
    base_url: typing.Optional[str] = None
    # A mapping of requests using the cache_key_for_request. Multiple resolvers
    # could attempt to fetch the same resource, using this we can limit to at
    # most one request per cache key.
    memoized_requests: typing.Dict[str, typing.Awaitable]

    # Timeout for an individual request in seconds.
    timeout: int = 5

    # Resource name for the type that this datasource returns by default this
    # will use the class name of the datasource.
    resource_name: typing.Optional[str] = None

    def __init__(
        self,
        request: typing.Any,
        client: typing.Optional[httpx.AsyncClient] = None,
    ):
        self.client = client or httpx.AsyncClient()
        # close the client if this instance opened it
        self._should_close_client = client is None
        self.request = request
        self.memoized_requests = {}
        self.assert_has_resource_name()

    def __del__(self):
        if self._should_close_client:
            LOG.debug(f"Closing httpx session for {self.resource_name}")
            asyncio.ensure_future(self.client.aclose())

    def assert_has_resource_name(self) -> None:
        if self.resource_name is None:
            self.resource_name = self.__class__.__name__

    def will_send_request(self, request: Request) -> Request:
        """Hook for subclasses to modify the request before it is sent.

        For example setting Authorization headers:

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

    def convert_to_object(self, json_obj):
        json_obj.update({"__typename": self.resource_name})
        return types.SimpleNamespace(**json_obj)

    async def did_receive_response(
        self, response: httpx.Response, request: Request
    ) -> typing.Any:
        """Hook to alter the response from the server.

        example::

            async def did_receive_response(
                self, response: httpx.Response, request: Request
            ) -> typing.Any:
                response.raise_for_status()
                return Widget(**response.json())
        """
        response.raise_for_status()
        return response.json(object_hook=self.convert_to_object)

    async def get(self, path: str) -> typing.Any:
        """Preform a GET request

        :param path: path of the request
        """
        return await self.fetch("GET", path)

    async def post(self, path: str, body: typing.Any) -> typing.Any:
        """Preform a POST request

        :param path: path of the request
        :param body: body of the request
        """
        return await self.fetch("POST", path, body)

    async def patch(self, path: str, body: typing.Any) -> typing.Any:
        """Preform a PATCH request

        :param path: path of the request
        :param body: body of the request
        """
        return await self.fetch("PATCH", path, body)

    async def put(self, path: str, body: typing.Any) -> typing.Any:
        """Preform a PUT request

        :param path: path of the request
        :param body: body of the request
        """
        return await self.fetch("PUT", path, body)

    async def delete(self, path: str) -> typing.Any:
        """Preform a DELETE request

        :param path: path of the request
        """
        return await self.fetch("DELETE", path)

    async def fetch(
        self, method: str, path: str, body: typing.Any = None
    ) -> typing.Any:
        url = self.get_request_url(path)

        request = Request(url, method, body)

        request = self.will_send_request(request)

        cache_key = self.cache_key_for_request(request)

        @cacheable
        async def process_request():
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
