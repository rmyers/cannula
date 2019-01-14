import asyncio
import functools
import inspect
import logging
import os
import threading
import types
import typing
from concurrent.futures import ThreadPoolExecutor

import requests

from cannula.context import Context

LOG = logging.getLogger('cannula.datasource.http')
MAX_WORKERS = int(os.getenv('CANNULA_HTTP_MAX_WORKERS', 4))


class DataSourceError(Exception):
    pass


class FutureSession(requests.Session):
    """Wrap requests session to allow requests to be async"""

    def __init__(self, max_workers=MAX_WORKERS, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def request(self, *args, **kwargs):
        function = functools.partial(requests.Session.request, self)
        return self.executor.submit(function, *args, **kwargs)

    def close(self):
        super().close()
        self.executor.shutdown()


class ThreadSafeCacheable:
    # see: https://stackoverflow.com/a/46723144

    def __init__(self, coroutine):
        self.coroutine = coroutine
        self.done = False
        self.result = None
        self.lock = threading.Lock()

    def __await__(self):
        while True:
            if self.done:
                return self.result
            if self.lock.acquire(blocking=False):
                self.result = yield from self.coroutine.__await__()
                self.done = True
                return self.result
            else:
                yield from asyncio.sleep(0.005)


def cacheable(f):
    def wrapped(*args, **kwargs):
        r = f(*args, **kwargs)
        return ThreadSafeCacheable(r)
    return wrapped


class HTTPContext(Context):
    http_session = FutureSession()


class Request(typing.NamedTuple):
    url: str
    method: str
    body: typing.Any = None
    headers: typing.Dict = {}


class HTTPDataSource:

    # The base url of this resource
    base_url: str = None
    # A mapping of requests using the cache_key_for_request. Multiple resolvers
    # could attempt to fetch the same resource, using this we can limit to at
    # most one request per cache key.
    memoized_requests: typing.Dict[str, typing.Awaitable]

    # Max number of worker argument to ThreadPoolExecutor
    max_workers: int = 4

    # Timeout for an individual request in seconds.
    timeout: int = 5

    def __init__(self, context):
        self.context = context
        self.memoized_requests = {}
        self.assert_has_http_session(context)

    def assert_has_http_session(self, context: Context) -> None:
        if not hasattr(context, 'http_session'):
            raise AttributeError('Context missing http_session did you subclass HTTPContext?')

    def will_send_request(self, request: Request) -> Request:
        """Hook for subclasses to modify the request before it is sent.

        For example setting Authorization headers:

            def will_send_request(self, request):
                request.headers = {'Authorization': self.context.token}
                return request
        """
        return request

    def cache_key_for_request(self, request: Request) -> str:
        return request.url

    def get_request_url(self, path: str) -> str:
        if path.startswith(('https://', 'http://')):
            return path

        if self.base_url is not None:
            if path.startswith('/'):
                path = path[1:]

            if self.base_url.endswith('/'):
                return f'{self.base_url}{path}'

            return f'{self.base_url}/{path}'

        return path

    def did_receive_error(self, error: Exception, request: Request):
        raise error

    async def did_receive_response(self, response: requests.Response, request: Request)-> None:
        response.raise_for_status()
        # if callable(response.text):
        #     import json
        #     body = await response.text(encoding='utf-8')
        #     return json.loads(body, object_hook=lambda d: types.SimpleNamespace(**d))
        return response.json(object_hook=lambda d: types.SimpleNamespace(**d))

    async def get(self, path: str) -> typing.Awaitable:
        return await self.fetch('GET', path)

    async def post(self, path: str, body: typing.Any) -> typing.Awaitable:
        return await self.fetch('POST', path, body)

    async def patch(self, path: str, body: typing.Any) -> typing.Awaitable:
        return await self.fetch('PATCH', path, body)

    async def put(self, path: str, body: typing.Any) -> typing.Awaitable:
        return await self.fetch('PUT', path, body)

    async def delete(self, path: str) -> typing.Awaitable:
        return await self.fetch('DELETE', path)

    async def fetch(
        self,
        method: str,
        path: str,
        body: typing.Any = None
    )-> typing.Awaitable:
        url = self.get_request_url(path)

        request = Request(url, method, body)

        request = self.will_send_request(request)

        cache_key = self.cache_key_for_request(request)

        @cacheable
        async def process_request():
            try:
                future = self.context.http_session.request(
                    request.method,
                    request.url,
                    data=request.body,
                    headers=request.headers,
                    timeout=self.timeout,
                    # ssl=False,
                )
                await asyncio.sleep(0.005)
                if inspect.isawaitable(future):
                    response = await future
                elif hasattr(future, 'result'):
                    response = future.result()
                else:
                    response = future
            except Exception as exc:
                return self.did_receive_error(exc, request)
            else:
                return await self.did_receive_response(response, request)

        # await asyncio.sleep(0.01)
        # return await process_request()

        if request.method == 'GET':
            promise = self.memoized_requests.get(cache_key)
            if promise is not None:
                LOG.debug(f'cache found for {self.__class__.__name__}')
                return await promise

            self.memoized_requests[cache_key] = process_request()
            LOG.debug(f'I have been cached as {cache_key}')
            # await asyncio.sleep(0.01)
            return await self.memoized_requests[cache_key]
        else:
            self.memoized_requests.pop(cache_key, None)
            return await process_request()
