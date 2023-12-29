import cannula
from cannula.middleware import MockMiddleware

schema = cannula.gql(
    """
    type Brocoli {
        taste: String
    }
    type Message {
        text: String
        number: Int
        float: Float
        isOn: Boolean
        id: ID
        brocoli: Brocoli
    }
    type Query {
        mockity: [Message]
    }
"""
)

sample_query = cannula.gql(
    """{
    mockity {
      text
      number
      float
      isOn
      id
      brocoli {
        taste
      }
    }
}
"""
)

default = cannula.API(
    schema=schema,
    middleware=[MockMiddleware()],
)


print(
    f"""
  Results with the default 'mock_all=True'. Since the result
  is a list you will get a random number of results unless
  you specify '__list_length' in mock_objects:
  {default.call_sync(sample_query).data}
"""
)


custom_mocks = {
    "String": "This will be used for all Strings",
    "Int": 42,
    "Brocoli": {"taste": "Delicious"},
    "Query": {"mockity": [{"isOn": False, "brocoli": {}}]},
}

custom = cannula.API(
    schema=schema,
    middleware=[
        MockMiddleware(mock_objects=custom_mocks, mock_all=True),
    ],
)

print(
    f"""
  Custom `mock_objects` with `mock_all=True` will return
  a fake result for every field:
  {custom.call_sync(sample_query).data}
"""
)

limited_mocks = cannula.API(
    schema=schema,
    middleware=[
        MockMiddleware(mock_objects=custom_mocks, mock_all=False),
    ],
)

print(
    f"""
  Limited mocks with `mock_all=False` will only return
  fake results for fields mocked in `mock_objects`:
  {limited_mocks.call_sync(sample_query).data}
"""
)
