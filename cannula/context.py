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

C = typing.TypeVar("C")
R = typing.TypeVar("R")


class ResolveInfo(typing.Generic[C], GraphQLResolveInfo):
    """
    This class is strictly to help with type checking. You can use
    this as the `info` arg in a revolver to assist with type hints
    and code completion::

        import typing
        import cannula

        class CustomContext(cannula.Context):
            widgets = widget_datasource()


        async def get_widgets(
            info: cannual.ResolveInfo[CustomContext]
        ) -> typing.List[Widget]:

            # type checker will be able to verify `get_widgets`
            # has the correct return type `list[Widget]`
            return info.context.widgets.get_widgets()
    """

    context: C


class Context(typing.Generic[R]):
    """Default Context Base

    Subclasses should implement a handle_request method to provide any
    extra functionality they need.
    """

    request: R

    def __init__(self, request: R):
        self.request = self.handle_request(request)

    @classmethod
    def init(cls, request: R):
        return cls(request)

    def handle_request(self, request: R) -> R:
        return request
