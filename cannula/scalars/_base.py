import abc
import typing


Input = typing.TypeVar("Input")
Output = typing.TypeVar("Output")


class ModuleImport(typing.NamedTuple):
    module: str
    klass: str


class ScalarInterface(typing.Protocol):
    name: str
    input_module: ModuleImport
    output_module: ModuleImport

    @staticmethod
    def serialize(value: typing.Any) -> typing.Any: ...

    @staticmethod
    def parse_value(value: typing.Any) -> typing.Any: ...


class ScalarType(typing.Generic[Input, Output]):
    """Scalar Type

    This class is intended to assist in generating well typed custom scalars.
    This class is a Generic type that expects two concrete types, `Input` and
    `Output`. `Input` is the raw python type and `Output` is a serializable
    type like `str`, `int` that is safe for JSON encoding.

    To use a custom type you must first add this type definition to your schema::

        scalar Datetime

    Next you need to create a subclass of `ScalarType` like::

        from datetime import datetime

        class Datetime(
            ScalarType[datetime, str],  # Input is the first type and Output is the second
            name="Datetime",  # Optional scalar name, by default the class name will be used.
        ):

            @staticmethod
            def serialize(value: datetime) -> str:
                return value.isoformat()

            @staticmethod
            def parse_value(value: str) -> datetime:
                return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
    """

    name: typing.ClassVar[str]
    input_module: typing.ClassVar[ModuleImport]
    output_module: typing.ClassVar[ModuleImport]

    def __init_subclass__(cls, name: typing.Optional[str] = None) -> None:
        bases = cls.__orig_bases__  # type: ignore
        for base in bases:
            if base.__name__ == "ScalarType":
                # lookup the input and output types for building imports
                _input, _output = typing.get_args(base)
                cls.input_module = ModuleImport(_input.__module__, _input.__name__)
                cls.output_module = ModuleImport(_output.__module__, _output.__name__)

        cls.name = name or cls.__name__
        return super().__init_subclass__()

    @staticmethod
    @abc.abstractmethod
    def serialize(value: Input) -> Output: ...

    @staticmethod
    @abc.abstractmethod
    def parse_value(value: Output) -> Input: ...
