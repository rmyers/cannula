"""
Context is how you can share information between resolvers. By default when
a request comes in cannula will create a context instance with the request
as an attribute. Then this is added to the GraphQLResolve info and passed
as the second argument to resolvers.

Example Resolver::

    aysnc def get_something(info: ResolveInfo[Context]):
        original_request = info.context.request
        if not can_access_something(original_request):
            raise AccessDenied("you do not have permission!")
        return await get_something()

Context Reference
-----------------
"""

import typing
from graphql import GraphQLResolveInfo
from starlette.requests import Request
from starlette.datastructures import State

C = typing.TypeVar("C")
Settings = typing.TypeVar("Settings")


class ResolveInfo(typing.Generic[C], GraphQLResolveInfo):
    """
    This class is strictly to help with type checking. You can use
    this as the `info` arg in a revolver to assist with type hints
    and code completion::

        import typing
        import cannula

        class CustomContext(cannula.Context):
            widgets: widget_datasource

            def init(self):
                self.widgets = widget_datasource(args)


        async def get_widgets(
            info: cannual.ResolveInfo[CustomContext]
        ) -> typing.List[Widget]:

            # type checker will be able to verify `get_widgets`
            # has the correct return type `list[Widget]`
            return info.context.widgets.get_widgets()
    """

    context: C


def make_request(state: typing.Any = None) -> Request:
    """Generate a fake request to statisfy the contract."""
    return Request(scope={"type": "http", "headers": [], "state": state or {}})


class Context(typing.Generic[Settings]):
    """Default Context Base

    Subclasses should implement a handle_request method to provide any
    extra functionality they need.
    """

    request: Request
    config: Settings

    def __init__(
        self,
        *,
        request: typing.Optional[Request] = None,
        config: typing.Optional[Settings] = None,
        **kwargs,
    ):
        self.request = self.handle_request(request)
        self.config = self.handle_config(config)
        self.handle_kwargs(**kwargs)
        self.init()

    def init(self):
        """Hook for subclasses to initialize an instance of Context.

        This provides a convient way to add attributes to the object such as
        dataloaders specific to the application.
        """
        pass

    def handle_kwargs(self, **kwargs) -> None:
        """Hook for subclasses to setup any extra arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def handle_config(self, config: typing.Optional[Settings] = None) -> Settings:
        """Hook for subclasses to handle configuration setup."""
        return config or typing.cast(Settings, State())

    def handle_request(self, request: typing.Optional[Request] = None) -> Request:
        """Hook for subsclasses to handle request setup."""
        return request or make_request()
