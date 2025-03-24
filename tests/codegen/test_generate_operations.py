import pytest
from cannula import gql, build_and_extend_schema
from cannula.scalars.date import Datetime
from cannula.codegen.schema_analyzer import SchemaAnalyzer
from cannula.codegen.generate_operations import TemplateGenerator

# Test schema definition
TEST_SCHEMA = """
scalar Datetime

type User {
    id: ID!
    name: String!
    createdAt: Datetime!
    score: Float!
    age: Int!
}

type Query {
    users: [User]!
    user(id: ID!): User
}
"""

# Test query with multiple fields
TEST_QUERY = """
query GetUsers {
    users {
        id
        name
        createdAt
        score
        age
    }
}
"""

# Test query with fragment
TEST_QUERY_WITH_FRAGMENT = """
fragment UserFields on User {
    name
    createdAt
    score
}

query GetUsersWithFragment {
    users {
        id
        ...UserFields
        age
    }
}
"""

TEST_USER_QUERY = """
query GetUser($id: ID!) {
    user(id: $id) {
        id
        name
        createdAt
        score
        age
    }
}
"""


@pytest.fixture
def schema_analyzer():
    schema = build_and_extend_schema([TEST_SCHEMA], scalars=[Datetime])
    return SchemaAnalyzer(schema)


@pytest.fixture
def template_generator(schema_analyzer, tmp_path):
    return TemplateGenerator(schema_analyzer, tmp_path, force=True)


def test_basic_template_generation(template_generator, tmp_path):
    # Parse and generate template
    document = gql(TEST_QUERY)
    template_generator.generate(document)

    # Check if file was created
    expected_file = tmp_path / "GetUsers.html"
    assert expected_file.exists()

    # Read content and verify structure
    content = expected_file.read_text()
    assert 'id="GetUsers-result"' in content
    assert "for users in data.users" in content
    assert "users.name" in content
    assert "users.age" in content
    assert "users.score" in content
    assert "users.createdAt" in content


def test_object_template_generation(template_generator, tmp_path):
    # Parse and generate template
    document = gql(TEST_USER_QUERY)
    template_generator.generate(document)

    # Check if file was created
    expected_file = tmp_path / "GetUser.html"
    assert expected_file.exists()

    # Read content and verify structure
    content = expected_file.read_text()
    assert 'id="GetUser-result"' in content
    assert "data.user.id" in content
    assert "data.user.name" in content
    assert "data.user.age" in content
    assert "data.user.score" in content
    assert "data.user.createdAt" in content


def test_fragment_template_generation(template_generator, tmp_path):
    # Parse and generate template with fragment
    document = gql(TEST_QUERY_WITH_FRAGMENT)
    template_generator.generate(document)

    # Check if file was created
    expected_file = tmp_path / "GetUsersWithFragment.html"
    assert expected_file.exists()

    # Read content and verify structure
    content = expected_file.read_text()
    assert 'id="GetUsersWithFragment-result"' in content
    assert "for users in data.users" in content
    assert "users.id" in content
    assert "users.name" in content
    assert "users.age" in content
    assert "users.score" in content
    assert "users.createdAt" in content


def test_skip_existing_template(schema_analyzer, tmp_path):
    # Create generator without force flag
    generator = TemplateGenerator(schema_analyzer, tmp_path, force=False)

    # Create existing file
    template_path = tmp_path / "GetUsers.html"
    template_path.write_text("Existing content")
    original_content = template_path.read_text()

    # Try to generate template
    document = gql(TEST_QUERY)
    generator.generate(document)

    # Verify content wasn't changed
    assert template_path.read_text() == original_content


def test_force_overwrite_template(schema_analyzer, tmp_path):
    # Create generator with force flag
    generator = TemplateGenerator(schema_analyzer, tmp_path, force=True)

    # Create existing file
    template_path = tmp_path / "GetUsers.html"
    template_path.write_text("Existing content")

    # Generate template
    document = gql(TEST_QUERY)
    generator.generate(document)

    # Verify content was overwritten
    content = template_path.read_text()
    assert 'id="GetUsers-result"' in content
    assert content != "Existing content"


def test_anonymous_operation_handling(template_generator):
    # Query without operation name
    anonymous_query = """
    query {
        users {
            id
            name
        }
    }
    """
    document = gql(anonymous_query)
    template_generator.generate(document)
    # Should not raise any exceptions, but also shouldn't create a file


def test_nested_field_template(template_generator, tmp_path):
    # Query with nested fields
    nested_query = """
    query GetNestedUser {
        user(id: "1") {
            id
            name
            posts {
                title
                comments {
                    text
                }
            }
        }
    }
    """
    # Update schema to include nested types
    schema = build_and_extend_schema(
        [
            """
    type Comment {
        text: String!
    }

    type Post {
        title: String!
        comments: [Comment!]!
    }

    type User {
        id: ID!
        name: String!
        posts: [Post!]!
    }

    type Query {
        user(id: ID!): User
    }
    """
        ]
    )

    generator = TemplateGenerator(SchemaAnalyzer(schema), tmp_path, force=True)
    document = gql(nested_query)
    generator.generate(document)

    expected_file = tmp_path / "GetNestedUser.html"
    assert expected_file.exists()

    content = expected_file.read_text()
    assert "data.user.id" in content
    assert "data.user.name" in content
    assert "for posts in data.user.posts" in content
    assert "posts.title" in content
    assert "for comments in posts.comments" in content
    assert "comments.text" in content
