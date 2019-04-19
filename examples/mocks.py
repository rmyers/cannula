"""
Automatic Mocks Example
-----------------------

This shows off how the automatic mocking works. All you need to do is specify
`mocks=True` and optionally `mock_objects` to the API.

Run this program multiple times to see how the data is randomly generated:

    $ PYTHONPATH=../ python3 mocks.py

You can change the `schema` or `sample_query` as well to see how the data
automatically changes too.
"""

import logging

import cannula
from cannula.middleware import MockMiddleware, DebugMiddleware

logging.basicConfig(level=logging.DEBUG)

schema = cannula.gql("""
  type Veggy {
    name: String
    id: ID
  }
  type Brocoli {
    name: String
    id: ID
    taste: String
    vegatable: Veggy
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
""")

sample_query = cannula.gql("""{
  mockity {
    text
    number
    float
    isOn
    id
    brocoli {
      name
      id
      vegatable {
        name
        id
      }
    }
  }
}
""")

default = cannula.API(
  __name__,
  schema=schema,
  middleware=[
    MockMiddleware(),
    DebugMiddleware(),
  ],
)


print(f'\nDEFAULT:\n{default.call_sync(sample_query)}')


custom_mocks = {
  'String': 'This will be used for all Strings',
  'Int': 42,
  'Veggy': {
    'name': "HOT STUFF",
    'id': "999999"
  }
}

custom = cannula.API(
  __name__,
  schema=schema,
  middleware=[
    MockMiddleware(
      mock_objects=custom_mocks
    ),
  ],
)

print(f'\nCUSTOM:\n{custom.call_sync(sample_query)}')
