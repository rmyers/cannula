import cannula

schema = cannula.gql(
    """
    type Sender {
        name: String
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

    class MockSender:
        __typename__ = "Sender"

    obj_type_name = thing_type.resolve_type(MockSender(), None, None)
    assert obj_type_name == "Sender"
    dict_type_name = thing_type.resolve_type({"__typename": "Message"}, None, None)
    assert dict_type_name == "Message"
    none_type_name = thing_type.resolve_type(None, None, None)
    assert none_type_name is None
