from graphql import GraphQLError
from pydantic import BaseModel, Field, ValidationError
import pytest

from cannula.errors import format_errors


class BasicModel(BaseModel):
    count: int = Field(..., gt=0)
    name: str = Field(..., min_length=3)


class NestedModel(BaseModel):
    nested: BasicModel
    other: bool


@pytest.mark.parametrize(
    "error, message, extensions",
    [
        pytest.param(
            GraphQLError("I borked it"),
            "I borked it",
            None,
            id="basic-error",
        ),
    ],
)
async def test_format_errors(error, message, extensions):
    formatted = format_errors(errors=[error])
    assert formatted
    assert formatted[0].get("message") == message, formatted
    assert formatted[0].get("extensions") == extensions, formatted


async def test_pydantic():

    try:
        NestedModel.model_validate_json(
            '{"nested": {"count": "not correct int", "name": "Bob"}, "other": false}',
        )
        assert False, "Model validation should have failed"
    except ValidationError as e:
        pass
        error = GraphQLError("something went wrong", original_error=e)

        formatted = format_errors(errors=[error])
        assert formatted is not None
        assert (
            formatted[0].get("message") == "Please enter a valid number for 'count'"
        ), formatted
