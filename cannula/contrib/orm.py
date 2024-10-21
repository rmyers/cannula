import typing
from dataclasses import fields

from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Self


DBModel = typing.TypeVar("DBModel", bound=DeclarativeBase)


class DataclassInstance(typing.Protocol):
    __dataclass_fields__: typing.ClassVar[dict[str, typing.Any]]


class DBMixin(typing.Generic[DBModel]):
    """Extend dataclass to include a `from_db` factory function.

    This is useful if you are using something like sqlalchemy for your
    database access. With this decorator you can then initialize the
    GraphQL object classes with the model from your ORM. As long as
    the required fields are present. All extra fields from the model
    will be ignored.

    Example::

        from cannula.contrib.orm import DBMixin
        from models import Widget as DBWidget
        from ._generated import WidgetTypeBase

        class Widget(WidgetTypeBase, DBMixin[DBWidget]):
            pass

        async def get_widgets(info) -> list[Widget]
            db_objects = await select_from_database(DBWidget)
            return [Widget.from_db(obj) for obj in db_objects]

    The resulting init function will also continue to accept kwargs
    and can override a field that is in the database if needed::

        widget = Widget.from_db(db_model, name="something else")
        assert widget.name == "something else"
    """

    _db_model: DBModel

    @classmethod
    def from_db(cls, db_obj: DBModel, **kwargs) -> Self:
        model_kwargs = db_obj.__dict__
        model_kwargs.update(kwargs)
        expected_fields = {
            field.name for field in fields(typing.cast(DataclassInstance, cls))
        }
        cleaned_kwargs = {
            key: value for key, value in model_kwargs.items() if key in expected_fields
        }
        obj = cls(**cleaned_kwargs)
        obj._db_model = db_obj
        return obj
