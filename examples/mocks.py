import asyncio
import typing
import sys

import cannula

my_schema = """
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

api = cannula.API(__name__, schema=my_schema, mocks=True)


sample_query = """{
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
"""

print(api.call_sync(sample_query, None))
