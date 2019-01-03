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

from graphql.language import parse

import cannula

schema = """
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
    isOn: Boolean
    id: ID
    brocoli: Brocoli
  }
  extend type Query {
    mockity(input: String): [Message]
  }
"""

sample_query = parse("""{
  mockity(input: "ignored") {
    text
    number
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

default = cannula.API(__name__, schema=schema, mocks=True)


print(f'\nDEFAULT:\n{default.call_sync(sample_query)}')


custom_mocks = {
  'String': 'This will be used for all Strings',
  'Int': 42,
}

custom = cannula.API(__name__, schema=schema, mocks=True, mock_objects=custom_mocks)

print(f'\nCUSTOM:\n{custom.call_sync(sample_query)}')
