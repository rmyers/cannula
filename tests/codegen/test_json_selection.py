from cannula.codegen.json_selection import (
    JSONSelectionParser,
    JSONResponseMapper,
    SelectionPath,
    apply_selection,
)


def test_selection_path_creation():
    """Test that SelectionPath dataclass is created correctly"""
    path = SelectionPath(root="products", fields=["id", "name"], is_array=True)

    assert path.root == "products"
    assert path.fields == ["id", "name"]
    assert path.is_array is True


def test_parse_with_dollar_root():
    """Test parsing a selection string with $ root notation"""
    selection = "$.products { id name price }"
    path = JSONSelectionParser.parse(selection)

    assert path.root == "products"
    assert path.fields == ["id", "name", "price"]
    assert path.is_array is False


def test_parse_without_dollar_root():
    """Test parsing a selection string without $ root notation"""
    selection = "products { id name }"
    path = JSONSelectionParser.parse(selection)

    assert path.root == "products"
    assert path.fields == ["id", "name"]
    assert path.is_array is False


def test_parse_with_no_root():
    """Test parsing a selection string with no root"""
    selection = "{ id name category }"
    path = JSONSelectionParser.parse(selection)

    assert path.root == ""
    assert path.fields == ["id", "name", "category"]
    assert path.is_array is False


def test_parse_array_notation():
    """Test parsing a selection string with array notation"""
    selection = "$.products[] { id name }"
    path = JSONSelectionParser.parse(selection)

    assert path.root == "products"
    assert path.fields == ["id", "name"]
    assert path.is_array is True


def test_parse_asterisk_array_notation():
    """Test parsing a selection string with [*] array notation"""
    selection = "$.products[*] { id name }"
    path = JSONSelectionParser.parse(selection)

    assert path.root == "products"
    assert path.fields == ["id", "name"]
    assert path.is_array is True


def test_parse_with_extra_whitespace():
    """Test parsing a selection string with extra whitespace"""
    selection = "  $.products  {  id   name  price  }  "
    path = JSONSelectionParser.parse(selection)

    assert path.root == "products"
    assert path.fields == ["id", "name", "price"]
    assert path.is_array is False


def test_get_value_at_path_empty_path():
    """Test getting a value with an empty path"""
    data = {"products": [{"id": 1}]}
    result = JSONResponseMapper.get_value_at_path(data, "")

    assert result == data


def test_get_value_at_path_simple():
    """Test getting a value with a simple path"""
    data = {"products": [{"id": 1}], "meta": {"count": 10}}
    result = JSONResponseMapper.get_value_at_path(data, "meta.count")

    assert result == 10


def test_get_value_at_path_nested():
    """Test getting a value with a nested path"""
    data = {"data": {"user": {"profile": {"name": "John"}}}}
    result = JSONResponseMapper.get_value_at_path(data, "data.user.profile.name")

    assert result == "John"


def test_get_value_at_path_not_found():
    """Test getting a value with a path that doesn't exist"""
    data = {"products": []}
    result = JSONResponseMapper.get_value_at_path(data, "orders.items")

    assert result is None


def test_get_value_at_path_with_default():
    """Test getting a value with a default value"""
    data = {"products": []}
    result = JSONResponseMapper.get_value_at_path(data, "orders", default=[])

    assert result == []


def test_get_value_at_path_non_dict():
    """Test getting a value when intermediate path is not a dict"""
    data = {"products": 123}
    result = JSONResponseMapper.get_value_at_path(data, "products.items")

    assert result is None


def test_map_response_single_object():
    """Test mapping a single object response"""
    data = {
        "product": {
            "id": 1,
            "name": "Product 1",
            "description": "Desc",
            "price": 100,
        }
    }
    selection = SelectionPath(root="product", fields=["id", "name"], is_array=False)

    result = JSONResponseMapper.map_response(data, selection)

    assert result == {"id": 1, "name": "Product 1"}


def test_map_response_array():
    """Test mapping an array response"""
    data = {
        "products": [
            {"id": 1, "name": "Product 1", "price": 100},
            {"id": 2, "name": "Product 2", "price": 200},
        ]
    }
    selection = SelectionPath(root="products", fields=["id", "name"], is_array=True)

    result = JSONResponseMapper.map_response(data, selection)

    assert result == [
        {"id": 1, "name": "Product 1"},
        {"id": 2, "name": "Product 2"},
    ]


def test_map_response_array_with_single_item():
    """Test mapping a non-array as array when is_array=True"""
    data = {"product": {"id": 1, "name": "Product 1", "price": 100}}
    selection = SelectionPath(root="product", fields=["id", "name"], is_array=True)

    result = JSONResponseMapper.map_response(data, selection)

    assert result == [{"id": 1, "name": "Product 1"}]


def test_map_response_array_with_none():
    """Test mapping None as array when is_array=True"""
    data = {"products": None}
    selection = SelectionPath(root="products", fields=["id", "name"], is_array=True)

    result = JSONResponseMapper.map_response(data, selection)

    assert result == []


def test_apply_selection_object():
    """Test applying selection to an object"""
    data = {
        "product": {
            "id": 1,
            "name": "Product 1",
            "description": "A great product",
            "price": 100,
        }
    }
    selection = "$.product { id name }"

    result = apply_selection(data, selection)

    assert result == {"id": 1, "name": "Product 1"}


def test_apply_selection_array():
    """Test applying selection to an array"""
    data = {
        "products": [
            {"id": 1, "name": "Product 1", "price": 100},
            {"id": 2, "name": "Product 2", "price": 200},
        ]
    }
    selection = "$.products[] { id name }"

    result = apply_selection(data, selection)

    assert result == [
        {"id": 1, "name": "Product 1"},
        {"id": 2, "name": "Product 2"},
    ]


def test_apply_selection_no_root():
    """Test applying selection with no root path"""
    data = {"id": 1, "name": "Product 1", "description": "Desc", "price": 100}
    selection = "{ id name }"

    result = apply_selection(data, selection)

    assert result == {"id": 1, "name": "Product 1"}


def test_apply_selection_nested_path():
    """Test applying selection with a nested path"""
    data = {
        "data": {
            "products": [
                {"id": 1, "name": "Product 1", "price": 100},
                {"id": 2, "name": "Product 2", "price": 200},
            ]
        }
    }
    selection = "$.data.products[] { id name }"

    result = apply_selection(data, selection)

    assert result == [
        {"id": 1, "name": "Product 1"},
        {"id": 2, "name": "Product 2"},
    ]


# Integration test with a more complex example
def test_complex_integration():
    """Test the full selection functionality with a complex nested structure"""
    # Sample response that might come from an API
    api_response = {
        "data": {
            "products": [
                {
                    "id": "prod-1",
                    "name": "Laptop",
                    "price": 1299.99,
                    "specs": {"cpu": "i7", "ram": "16GB"},
                    "tags": ["electronics", "computers"],
                },
                {
                    "id": "prod-2",
                    "name": "Smartphone",
                    "price": 799.99,
                    "specs": {"cpu": "A15", "ram": "8GB"},
                    "tags": ["electronics", "mobile"],
                },
            ],
            "pagination": {"total": 2, "page": 1, "pages": 1},
        }
    }

    # Select just product IDs and names
    selection = "$.data.products[] { id name }"
    result = apply_selection(api_response, selection)

    assert result == [
        {"id": "prod-1", "name": "Laptop"},
        {"id": "prod-2", "name": "Smartphone"},
    ]

    # Test selection of pagination info
    pagination_selection = "$.data.pagination { total pages }"
    pagination_result = apply_selection(api_response, pagination_selection)

    assert pagination_result == {"total": 2, "pages": 1}
