import asyncio
import dataclasses
import typing

GraphModel = typing.TypeVar("GraphModel")


def cacheable(f):
    """Decorator that is used to allow coroutines to be cached.

    Solves the issue of `cannot reuse already awaited coroutine`

    Example::

        _memoized: dict[str, Awaitable]

        async def get(self, pk: str):
            cache_key = f"get:{pk}"

            @cacheable
            async def process_get():
                return await session.get(pk)

            if results := _memoized.get(cache_key):
                return await results

            _memoized[cache_key] = process_get()
            return await _memoized[cache_key]

        # These results will share the same results and not
        results = await asyncio.gather(get(1), get(1), get(1))

    """

    def wrapped(*args, **kwargs):
        r = f(*args, **kwargs)
        return asyncio.ensure_future(r)

    return wrapped


def expected_fields(obj: typing.Any) -> set[str]:
    """Extract all the fields that are on the object.

    This is used when constructing a new instance from a datasource.
    """
    if dataclasses.is_dataclass(obj):
        return {field.name for field in dataclasses.fields(obj)}

    if hasattr(obj, "model_fields"):
        return {field for field in obj.model_fields}

    raise ValueError(
        "Invalid model for 'GraphModel' must be a dataclass or pydantic model"
    )
