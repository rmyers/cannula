from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request

# Import the functions to test
from cannula.handlers.forms import (
    parse_nested_form,
    process_form_data,
    set_nested_value,
)


# Test set_nested_value function
def test_set_nested_value_simple():
    data = {}
    set_nested_value(data, "name", "John")
    assert data == {"name": "John"}


def test_set_nested_value_dot_notation():
    data = {}
    set_nested_value(data, "profile.name", "John")
    assert data == {"profile": {"name": "John"}}


def test_set_nested_value_multiple_dots():
    data = {}
    set_nested_value(data, "user.profile.address.city", "New York")
    assert data == {"user": {"profile": {"address": {"city": "New York"}}}}


def test_set_nested_value_array_notation():
    data = {}
    set_nested_value(data, "items[0]", "item1")
    assert data == {"items": ["item1"]}


def test_set_nested_value_array_with_objects():
    data = {}
    set_nested_value(data, "users[0].name", "John")
    set_nested_value(data, "users[0].email", "john@example.com")
    set_nested_value(data, "users[1].name", "Jane")
    assert data == {
        "users": [{"name": "John", "email": "john@example.com"}, {"name": "Jane"}]
    }


def test_set_nested_value_complex_structure():
    data = {}
    set_nested_value(data, "company.departments[0].name", "Engineering")
    set_nested_value(data, "company.departments[0].employees[0].name", "John")
    set_nested_value(data, "company.departments[0].employees[1].name", "Jane")
    set_nested_value(data, "company.departments[1].name", "Marketing")

    assert data == {
        "company": {
            "departments": [
                {
                    "name": "Engineering",
                    "employees": [{"name": "John"}, {"name": "Jane"}],
                },
                {"name": "Marketing"},
            ]
        }
    }


def test_set_nested_value_array_index_gap():
    data = {}
    set_nested_value(data, "items[2]", "item3")
    assert data == {"items": [{}, {}, "item3"]}


def test_set_nested_value_array_direct_assignment():
    """Test direct assignment to array elements without further nesting"""
    data = {}

    # Assign direct values to array elements
    set_nested_value(data, "tags[0]", "python")
    set_nested_value(data, "tags[1]", "fastapi")
    set_nested_value(data, "tags[2]", "starlette")

    # Assign a direct value to a nested array element
    set_nested_value(data, "user.skills[0]", "coding")
    set_nested_value(data, "user.skills[1]", "testing")

    # Assign an object to an array element (still direct assignment)
    set_nested_value(
        data,
        "items[0]",
        {"id": 1, "name": "Item 1"},  # type: ignore
    )

    assert data == {
        "tags": ["python", "fastapi", "starlette"],
        "user": {"skills": ["coding", "testing"]},
        "items": [{"id": 1, "name": "Item 1"}],
    }


# Test process_form_data function
def test_process_form_data_simple():
    form_data = FormData([("name", "John"), ("email", "john@example.com")])
    result = process_form_data(form_data)
    assert result == {"name": "John", "email": "john@example.com"}


def test_process_form_data_nested():
    form_data = FormData(
        [
            ("name", "John"),
            ("profile.interests", "coding"),
            ("profile.color", "blue"),
            ("profile.likes_cake", "true"),
        ]
    )
    result = process_form_data(form_data)
    assert result == {
        "name": "John",
        "profile": {"interests": "coding", "color": "blue", "likes_cake": "true"},
    }


def test_process_form_data_arrays():
    form_data = FormData(
        [
            ("preferences[0].name", "theme"),
            ("preferences[0].value", "dark"),
            ("preferences[1].name", "notifications"),
            ("preferences[1].value", "true"),
        ]
    )
    result = process_form_data(form_data)
    assert result == {
        "preferences": [
            {"name": "theme", "value": "dark"},
            {"name": "notifications", "value": "true"},
        ]
    }


def test_process_form_data_mixed():
    form_data = FormData(
        [
            ("name", "John"),
            ("email", "john@example.com"),
            ("profile.interests", "coding"),
            ("preferences[0].name", "theme"),
            ("preferences[0].value", "dark"),
            ("address.street", "123 Main St"),
            ("address.city", "New York"),
        ]
    )
    result = process_form_data(form_data)
    assert result == {
        "name": "John",
        "email": "john@example.com",
        "profile": {"interests": "coding"},
        "preferences": [{"name": "theme", "value": "dark"}],
        "address": {"street": "123 Main St", "city": "New York"},
    }


# Test with file uploads
def test_process_form_data_with_files(mocker):
    # Create mock upload files
    mock_avatar = mocker.MagicMock(spec=UploadFile)
    mock_avatar.filename = "avatar.jpg"

    mock_document = mocker.MagicMock(spec=UploadFile)
    mock_document.filename = "document.pdf"

    form_data = FormData(
        [
            ("name", "John"),
            ("profile.avatar", mock_avatar),
            ("documents[0].file", mock_document),
        ]
    )

    result = process_form_data(form_data)

    assert result["name"] == "John"
    assert result["profile"]["avatar"] is mock_avatar
    assert result["documents"][0]["file"] is mock_document


# Test parse_nested_form with mocked request
async def test_parse_nested_form(mocker):
    # Create a mock request
    mock_request = mocker.AsyncMock(spec=Request)

    # Create mock form data
    form_data = FormData(
        [
            ("name", "John"),
            ("profile.interests", "coding"),
            ("preferences[0].name", "theme"),
        ]
    )

    # Configure the mock to return our form data
    mock_request.form = mocker.AsyncMock(return_value=form_data)

    # Call the function with our mock
    result = await parse_nested_form(mock_request)

    # Check the results
    assert result == {
        "name": "John",
        "profile": {"interests": "coding"},
        "preferences": [{"name": "theme"}],
    }

    # Verify that form() was called
    mock_request.form.assert_called_once()


# Test with multipart form data including files
async def test_parse_nested_form_with_multipart(mocker):
    # Create a mock request
    mock_request = mocker.AsyncMock(spec=Request)

    # Create mock upload files
    mock_avatar = mocker.MagicMock(spec=UploadFile)
    mock_avatar.filename = "avatar.jpg"

    # Create mock form data with files
    form_data = FormData(
        [
            ("name", "John"),
            ("profile.avatar", mock_avatar),
            ("profile.interests", "coding"),
        ]
    )

    # Configure the mock to return our form data
    mock_request.form = mocker.AsyncMock(return_value=form_data)

    # Call the function with our mock
    result = await parse_nested_form(mock_request)

    # Check the results
    assert result["name"] == "John"
    assert result["profile"]["avatar"] is mock_avatar
    assert result["profile"]["interests"] == "coding"
