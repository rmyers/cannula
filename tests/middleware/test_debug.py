import logging
import typing
from unittest import mock

import cannula
from cannula.middleware import DebugMiddleware

SCHEMA = cannula.gql(
    """
  type Message {
    text: String @deprecated(reason: "Use `newField`.")
  }
  type Query {
    hello(who: String): Message
  }
"""
)


class Message(typing.NamedTuple):
    text: str


# Pre-parse your query to speed up your requests.
# Here is an example of how to pass arguments to your
# query functions.
SAMPLE_QUERY = cannula.gql(
    """
  query HelloWorld ($who: String!) {
    hello(who: $who) {
      text
    }
  }
"""
)


async def test_debug_middleware(mocker):
    mock_time = mocker.patch("time.perf_counter")
    mock_time.return_value = 0.00001

    logger = mock.Mock(spec=logging.Logger)
    api = cannula.API(
        __name__,
        schema=[SCHEMA],
        middleware=[DebugMiddleware(logger=logger)],
    )

    # The query resolver takes a source and info objects
    # and any arguments defined by the schema. Here we
    # only accept a single argument `who`.
    @api.resolver("Query")
    async def hello(_source, _info, who):
        return Message(f"Hello, {who}!")

    results = await api.call(SAMPLE_QUERY, variables={"who": "they"})
    assert results.data == {"hello": {"text": "Hello, they!"}}

    assert logger.debug.mock_calls == [
        mock.call("Resolving Query.hello expecting type Message"),
        mock.call(
            "Field Query.hello resolved: Message(text='Hello, they!') in 0.000000 seconds"
        ),
        mock.call("Resolving Message.text expecting type String"),
        mock.call("Field Message.text resolved: 'Hello, they!' in 0.000000 seconds"),
    ]
