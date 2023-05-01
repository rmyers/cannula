import cannula
from graphql import GraphQLObjectType, GraphQLString, GraphQLSchema

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
    boo: String
  }
"""
)

extensions = cannula.gql(
    """
  extend type Brocoli {
    color: String
  }
  extend type Query {
    fancy: [Message]
  }
"""
)

# schema = cannula.build_and_extend_schema([schema, extensions])

api = cannula.API(
    __name__,
    schema=[schema, extensions],
)

SAMPLE_QUERY = cannula.gql(
    """
  query HelloWorld {
    fancy {
      text
    }
  }
"""
)


print(api.call_sync(SAMPLE_QUERY))
