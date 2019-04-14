from graphql import parse, DocumentNode


def gql(schema: str) -> DocumentNode:
    """
    Helper utility to provide help mark up
    """
    return parse(schema)
