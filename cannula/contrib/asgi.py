import typing

import pydantic


class GraphQLPayload(pydantic.BaseModel):
    query: str
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None
    operation: typing.Optional[str] = None
