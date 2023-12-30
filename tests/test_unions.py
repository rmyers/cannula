import typing

import cannula


class Message(typing.NamedTuple):
    __typename = "Message"
    text: str
    other: str


class Email(typing.NamedTuple):
    __typename = "Email"
    text: str
    address: str


SCHEMA = cannula.gql(
    """
    type Message {
        text: String
        other: String
    }

    type Email {
        text: String
        address: String
    }

    union Notification = Message | Email

    type Query {
        notifications: [Notification]
    }
"""
)

QUERY = cannula.gql(
    """
    query Notifications {
        notifications {
            __typename
            ... on Email {
                text
                address
            }
            ... on Message {
                text
                other
            }
        }
    }
"""
)

NOTIFICATIONS = [
    Message(text="hello", other="message one"),
    Message(text="hello", other="message one"),
    Email(text="hello", address="jon@example.com"),
    Email(text="hello", address="jane@example.com"),
]

api = cannula.API(schema=SCHEMA)


@api.resolver("Query", "notifications")
async def get_notifications(parent, info) -> typing.List[typing.Any]:
    return NOTIFICATIONS


async def test_union_types():
    result = await api.call(QUERY)
    assert result.data is not None, result.errors
    notifications = result.data["notifications"]
    assert notifications == [
        {"__typename": "Message", "text": "hello", "other": "message one"},
        {"__typename": "Message", "text": "hello", "other": "message one"},
        {"__typename": "Email", "text": "hello", "address": "jon@example.com"},
        {"__typename": "Email", "text": "hello", "address": "jane@example.com"},
    ]
