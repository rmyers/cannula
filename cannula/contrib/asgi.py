import typing

import pydantic


class GraphQLPayload(pydantic.BaseModel):
    """Model representing a GraphQL request body."""

    query: str
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None
    operation: typing.Optional[str] = None
