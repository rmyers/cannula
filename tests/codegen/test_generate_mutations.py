import pytest

from cannula import gql, build_and_extend_schema
from cannula.scalars.date import Datetime
from cannula.codegen.schema_analyzer import SchemaAnalyzer
from cannula.codegen.generate_operations import TemplateGenerator

# Test schema with mutations
MUTATION_SCHEMA = """
scalar Datetime

input UserInput {
    name: String!
    email: String!
    age: Int
}

input PostInput {
    title: String!
    content: String!
    tags: [String!]
}

input CommentInput {
    text: String!
}

type User {
    id: ID!
    name: String!
    email: String!
    age: Int
    posts: [Post!]
}

type Post {
    id: ID!
    title: String!
    content: String!
    author: User!
    comments: [Comment!]!
}

type Comment {
    id: ID!
    text: String!
    author: User!
}

type CreateUserResult {
    user: User!
    token: String!
}

type CreatePostResult {
    post: Post!
}

type Mutation {
    createUser(input: UserInput!): CreateUserResult!
    createPost(userId: ID!, input: PostInput!): CreatePostResult!
    addComment(postId: ID!, input: CommentInput!): Comment!
}

type Query {
    users: [User]!
    user(id: ID!): User
    posts: [Post]!
    post(id: ID!): Post
}
"""

# Simple mutation for creating a user
CREATE_USER_MUTATION = """
mutation CreateUser($input: UserInput!) {
    createUser(input: $input) {
        user {
            id
            name
            email
        }
        token
    }
}
"""

# Mutation with multiple inputs and nested return fields
CREATE_POST_MUTATION = """
mutation CreatePost($userId: ID!, $input: PostInput!) {
    createPost(userId: $userId, input: $input) {
        post {
            id
            title
            content
            author {
                id
                name
            }
        }
    }
}
"""

# Mutation with nested input and return types
COMPLEX_MUTATION = """
mutation ComplexOperation($userId: ID!, $postInput: PostInput!) {
    createUser(input: {
        name: "Auto Generated",
        email: "auto@example.com",
        age: 30
    }) {
        user {
            id
            name
        }
        token
    }
    createPost(userId: $userId, input: $postInput) {
        post {
            id
            title
            content
            author {
                id
                name
                email
            }
            comments {
                id
                text
                author {
                    name
                }
            }
        }
    }
}
"""

# Simple mutation with no nested fields
ADD_COMMENT_MUTATION = """
mutation AddComment($postId: ID!, $input: CommentInput!) {
    addComment(postId: $postId, input: $input) {
        id
        text
    }
}
"""


@pytest.fixture
def mutation_schema_analyzer():
    schema = build_and_extend_schema([MUTATION_SCHEMA], scalars=[Datetime])
    return SchemaAnalyzer(schema)


@pytest.fixture
def mutation_template_generator(mutation_schema_analyzer, tmp_path):
    return TemplateGenerator(mutation_schema_analyzer, tmp_path, force=True)


def test_simple_mutation_template(mutation_template_generator, tmp_path):
    # Parse and generate template
    document = gql(CREATE_USER_MUTATION)
    mutation_template_generator.generate(document)

    # Check if form template was created
    form_file = tmp_path / "CreateUser_form.html"
    assert form_file.exists()

    # Check if result template was created
    result_file = tmp_path / "CreateUser_result.html"
    assert result_file.exists()

    # Verify form content
    form_content = form_file.read_text()
    assert "input.name" in form_content
    assert "input.email" in form_content
    assert "input.age" in form_content

    # Verify result content
    result_content = result_file.read_text()
    assert "data.createUser.user.id" in result_content
    assert "data.createUser.user.name" in result_content
    assert "data.createUser.user.email" in result_content
    assert "data.createUser.token" in result_content


def test_multi_input_mutation_template(mutation_template_generator, tmp_path):
    # Parse and generate template
    document = gql(CREATE_POST_MUTATION)
    mutation_template_generator.generate(document)

    # Check if form template was created
    form_file = tmp_path / "CreatePost_form.html"
    assert form_file.exists()

    # Check if result template was created
    result_file = tmp_path / "CreatePost_result.html"
    assert result_file.exists()

    # Verify form content
    form_content = form_file.read_text()
    assert "userId" not in form_content
    assert "input.title" in form_content
    assert "input.content" in form_content
    assert "input.tags" in form_content

    # Verify result content
    result_content = result_file.read_text()
    assert "data.createPost.post.id" in result_content
    assert "data.createPost.post.title" in result_content
    assert "data.createPost.post.content" in result_content
    assert "data.createPost.post.author.id" in result_content
    assert "data.createPost.post.author.name" in result_content


def test_simple_mutation_no_nested_fields(mutation_template_generator, tmp_path):
    # Parse and generate template
    document = gql(ADD_COMMENT_MUTATION)
    mutation_template_generator.generate(document)

    # Check if form and result templates were created
    form_file = tmp_path / "AddComment_form.html"
    result_file = tmp_path / "AddComment_result.html"
    assert form_file.exists()
    assert result_file.exists()

    # Verify form content
    form_content = form_file.read_text()
    assert "postId" not in form_content
    assert "text" in form_content

    # Verify result content
    result_content = result_file.read_text()
    assert "data.addComment.id" in result_content
    assert "data.addComment.text" in result_content


def test_complex_mutation_with_nested_fields(mutation_template_generator, tmp_path):
    # Parse and generate template
    document = gql(COMPLEX_MUTATION)
    mutation_template_generator.generate(document)

    # Check if templates were created
    form_file = tmp_path / "ComplexOperation_form.html"
    result_file = tmp_path / "ComplexOperation_result.html"
    assert form_file.exists()
    assert result_file.exists()

    # Verify form content
    form_content = form_file.read_text()
    assert "userId" not in form_content
    assert "postInput.title" in form_content
    assert "postInput.content" in form_content
    assert "postInput.tags" in form_content

    # Verify result content - check for nested structures
    result_content = result_file.read_text()

    # First operation result
    assert "data.createUser.user.id" in result_content
    assert "data.createUser.user.name" in result_content
    assert "data.createUser.token" in result_content

    # Second operation result with deeply nested fields
    assert "data.createPost.post.id" in result_content
    assert "data.createPost.post.title" in result_content
    assert "data.createPost.post.content" in result_content
    assert "data.createPost.post.author.id" in result_content
    assert "data.createPost.post.author.name" in result_content
    assert "data.createPost.post.author.email" in result_content

    # Check for nested list loop
    # TODO(rmyers) fix me!
    # assert "for comments in data.createPost.post.comments" in result_content
    assert "comments.id" in result_content
    assert "comments.text" in result_content
    assert "comments.author.name" in result_content


def test_nested_input_mutation(mutation_schema_analyzer, tmp_path):
    # Create a mutation with nested input objects
    nested_input_schema = """
    input AddressInput {
        street: String!
        city: String!
        country: String!
    }

    input ProfileInput {
        bio: String
        address: AddressInput!
        interests: [String!]
    }

    input ComplexUserInput {
        name: String!
        email: String!
        profile: ProfileInput!
    }

    type Address {
        street: String!
        city: String!
        country: String!
    }

    type Profile {
        bio: String
        address: Address!
        interests: [String!]
    }

    type ComplexUser {
        id: ID!
        name: String!
        email: String!
        profile: Profile!
    }

    type Mutation {
        createComplexUser(input: ComplexUserInput!): ComplexUser!
    }
    """

    schema = build_and_extend_schema([nested_input_schema])
    generator = TemplateGenerator(SchemaAnalyzer(schema), tmp_path, force=True)

    # Create a mutation with nested input
    nested_mutation = """
    mutation CreateComplexUser($input: ComplexUserInput!) {
        createComplexUser(input: $input) {
            id
            name
            email
            profile {
                bio
                address {
                    street
                    city
                    country
                }
                interests
            }
        }
    }
    """

    document = gql(nested_mutation)
    generator.generate(document)

    # Check if templates were created
    form_file = tmp_path / "CreateComplexUser_form.html"
    result_file = tmp_path / "CreateComplexUser_result.html"
    assert form_file.exists()
    assert result_file.exists()

    # Verify form content with deep nesting
    form_content = form_file.read_text()
    assert "input.name" in form_content
    assert "input.email" in form_content
    # TODO(rmyers): fix these
    # assert "input.profile.bio" in form_content
    # assert "input.profile.address.street" in form_content
    # assert "input.profile.address.city" in form_content
    # assert "input.profile.address.country" in form_content
    # assert "input.profile.interests" in form_content

    # Verify result content with nested objects
    result_content = result_file.read_text()
    assert "data.createComplexUser.id" in result_content
    assert "data.createComplexUser.name" in result_content
    assert "data.createComplexUser.email" in result_content
    assert "data.createComplexUser.profile.bio" in result_content
    assert "data.createComplexUser.profile.address.street" in result_content
    assert "data.createComplexUser.profile.address.city" in result_content
    assert "data.createComplexUser.profile.address.country" in result_content

    # Check for list handling
    assert (
        "for interests in data.createComplexUser.profile.interests" in result_content
        or "data.createComplexUser.profile.interests" in result_content
    )
