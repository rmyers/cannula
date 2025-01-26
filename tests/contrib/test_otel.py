import pytest
from unittest.mock import Mock, AsyncMock
from graphql import parse, GraphQLError, ExecutionResult
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
)

from cannula.contrib.otel import instrument_cannula


class MockCannulaAPI:
    """Mock CannulaAPI class for testing"""

    def __init__(self):
        self.call = AsyncMock()
        self._parse_document = Mock()
        self._validate = Mock()


@pytest.fixture
def api():
    """Create a mock CannulaAPI instance"""
    return MockCannulaAPI()


async def test_successful_string_query(api):
    """Test successful query with string document"""
    # Setup
    query = "query { hello }"
    parsed_doc = parse(query)
    api._parse_document.return_value = Mock(document_ast=parsed_doc, errors=[])
    api._validate.return_value = []
    api.call.return_value = ExecutionResult(data={"hello": "world"})

    # Instrument the API
    instrument_cannula(api)

    # Execute
    result = await api.call(
        document=query, operation_name="TestQuery", variables={"test": "var"}
    )

    # Verify
    assert result.data == {"hello": "world"}
    api._parse_document.assert_called_once_with(query)
    api._validate.assert_called_once_with(parsed_doc)


async def test_parsing_error(api):
    """Test handling of parsing errors"""
    # Setup
    query = "invalid query {"
    parse_error = GraphQLError("Syntax Error")
    api._parse_document.return_value = Mock(document_ast=None, errors=[parse_error])

    # Instrument the API
    instrument_cannula(api)

    # Execute
    result = await api.call(document=query)

    # Verify
    assert result.errors == [parse_error]
    assert result.data is None
    api._parse_document.assert_called_once_with(query)
    api._validate.assert_not_called()


async def test_validation_error(api):
    """Test handling of validation errors"""
    # Setup
    query = "query { hello }"
    parsed_doc = parse(query)
    validation_error = GraphQLError("Validation Error")
    api._parse_document.return_value = Mock(document_ast=parsed_doc, errors=[])
    api._validate.return_value = [validation_error]

    # Instrument the API
    instrument_cannula(api)

    # Execute
    result = await api.call(document=query)

    # Verify
    assert result.errors == [validation_error]
    assert result.data is None
    api._validate.assert_called_once_with(parsed_doc)


async def test_execution_error(api):
    """Test handling of execution errors"""
    # Setup
    query = "query { hello }"
    parsed_doc = parse(query)
    execution_error = GraphQLError("Execution Error")
    api._parse_document.return_value = Mock(document_ast=parsed_doc, errors=[])
    api._validate.return_value = []
    api.call.return_value = ExecutionResult(data=None, errors=[execution_error])

    # Instrument the API
    instrument_cannula(api)

    # Execute
    result = await api.call(document=query)

    # Verify
    assert result.errors == [execution_error]
    assert result.data is None


async def test_already_parsed_document(api):
    """Test handling of pre-parsed DocumentNode"""
    # Setup
    parsed_doc = parse("query { hello }")
    api._validate.return_value = []
    api.call.return_value = ExecutionResult(data={"hello": "world"})

    # Instrument the API
    instrument_cannula(api)

    # Execute
    result = await api.call(document=parsed_doc)

    # Verify
    assert result.data == {"hello": "world"}
    api._parse_document.assert_not_called()
    api._validate.assert_called_once_with(parsed_doc)


async def test_unexpected_exception(api):
    """Test handling of unexpected exceptions during execution"""
    # Setup
    query = "query { hello }"
    parsed_doc = parse(query)
    api._parse_document.return_value = Mock(document_ast=parsed_doc, errors=[])
    api._validate.return_value = []
    api.call.side_effect = Exception("Unexpected error")

    # Instrument the API
    instrument_cannula(api)

    # Execute and verify exception is raised
    with pytest.raises(Exception) as exc_info:
        await api.call(document=query)

    assert str(exc_info.value) == "Unexpected error"


async def test_span_attributes(api):
    """Test that span attributes are correctly set"""
    captured_spans = []

    # Create a custom SpanProcessor to capture spans
    class TestSpanProcessor(SimpleSpanProcessor):
        def __init__(self, span_exporter):
            self.span_exporter = span_exporter

        def on_start(self, span, parent_context):
            print(span)
            pass

        def on_end(self, span):
            captured_spans.append(span)

        def shutdown(self):
            pass

        def force_flush(self, timeout_millis=30000):
            pass

    # Setup
    provider = TracerProvider()
    provider.add_span_processor(TestSpanProcessor(SpanExporter()))
    trace.set_tracer_provider(provider)

    query = "query TestOp { hello }"
    parsed_doc = parse(query)
    api._parse_document.return_value = Mock(document_ast=parsed_doc, errors=[])
    api._validate.return_value = []
    api.call.return_value = ExecutionResult(data={"hello": "world"})

    # Instrument the API
    instrument_cannula(api)

    # Execute
    await api.call(document=query, operation_name="TestOp", variables={"test": "var"})

    # Verify spans were captured
    assert (
        len(captured_spans) >= 4
    ), f"Expected at least 4 spans, got {len(captured_spans)}"

    # Find the main request span
    request_span = next(
        (span for span in captured_spans if span.name == "graphql.request"), None
    )
    assert request_span is not None, "Could not find graphql.request span"

    # Verify span attributes
    assert request_span.attributes.get("graphql.operation.name") == "TestOp"
    assert request_span.attributes.get("graphql.document") == query

    # Verify child spans exist
    span_names = {span.name for span in captured_spans}
    assert "graphql.parse" in span_names, "Missing parse span"
    assert "graphql.validate" in span_names, "Missing validate span"
    assert "graphql.execute" in span_names, "Missing execute span"


def test_wrapper_preserves_function_metadata(api):
    """Test that the wrapper preserves the original function's metadata"""
    original_call = api.call
    instrument_cannula(api)

    assert api.call.__name__ == original_call.__name__
    assert api.call.__doc__ == original_call.__doc__
