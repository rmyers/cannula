from typing import cast
from unittest import mock
from graphql import GraphQLUnionType, GraphQLResolveInfo, parse

import cannula

schema = cannula.gql(
    """
    type Sender {
        name: String @deprecated(reason: "Use `email`.")
    }
    type Message {
        text: String
        sender: Sender
    }
    type Query {
        messages: [Message]
    }
"""
)

extensions = cannula.gql(
    """
    extend type Sender {
        email: String
    }
    extend type Query {
        get_sender_by_email(email: String): Sender
    }
"""
)


async def get_sender_by_email(email: str) -> dict:
    return {"email": email, "name": "tester"}


async def test_extentions_are_correct():
    api = cannula.API(__name__, schema=[schema, extensions])

    @api.resolver()
    async def get_sender_by_email(_root, _info, email: str) -> dict:
        return {"email": email, "name": "tester"}

    query = cannula.gql(
        """
        query Extentions {
            get_sender_by_email(email: "test@example.com") {
                name
                email
            }
        }
    """
    )
    results = await api.call(query)
    assert results.data == {
        "get_sender_by_email": {
            "name": "tester",
            "email": "test@example.com",
        }
    }


async def test_union_types():
    with_union = cannula.schema.build_and_extend_schema(
        [schema, "union Thing = Sender | Message"]
    )
    fixed = cannula.schema.fix_abstract_resolve_type(with_union)
    thing_type = fixed.get_type("Thing")
    assert thing_type is not None

    # Cast to union for type checking
    thing_union = cast(GraphQLUnionType, thing_type)
    assert thing_union.resolve_type is not None

    class MockSender:
        __typename__ = "Sender"

    resolve_info = mock.MagicMock(spec=GraphQLResolveInfo)

    obj_type_name = thing_union.resolve_type(MockSender(), resolve_info, thing_union)
    assert obj_type_name == "Sender"
    dict_type = thing_union.resolve_type(
        {"__typename": "Message"}, resolve_info, thing_union
    )
    assert dict_type == "Message"
    none_type_name = thing_union.resolve_type(None, resolve_info, thing_union)
    assert none_type_name is None


async def test_directives():
    document = parse('type Director { frank: String @cache(max: "50s") ted: String}')
    print(document.to_dict())
    parsed = document.to_dict()
    defs = parsed.get("definitions", [])
    # TODO get the directives to work
    assert len(defs[0].get("fields")) == 2
