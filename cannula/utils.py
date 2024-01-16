import dataclasses
import typing
import warnings

from graphql import parse, DocumentNode


def gql(schema: str) -> DocumentNode:
    """
    Helper utility to provide help mark up
    """
    return parse(schema)


@dataclasses.dataclass
class Directive:
    name: str
    args: typing.Dict[str, typing.Any]


class BaseMixin:
    __directives__: typing.Dict[str, typing.List[Directive]]

    def __getattribute__(self, __name) -> typing.Any:  # pragma: no cover
        try:
            __directives__ = super().__getattribute__("__directives__")
            directives = __directives__[__name]
            for directive in directives:
                if directive.name == "deprecated":
                    message = directive.args.get("reason")
                    warnings.warn(message, DeprecationWarning)
        except (AttributeError, KeyError):
            pass

        return super().__getattribute__(__name)
