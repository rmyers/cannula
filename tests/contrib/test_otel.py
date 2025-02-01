import asyncio
import pytest
from typing import AsyncIterable, List
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.trace import StatusCode, Span

from cannula.contrib.otel import create_instrumented_api


class MockSpanProcessor(SpanProcessor):
    """Custom span processor that captures spans for testing"""

    def __init__(self):
        self.spans: List[Span] = []

    def on_start(self, span: Span, parent_context):
        pass

    def on_end(self, span: Span):
        self.spans.append(span)

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        pass


spans = MockSpanProcessor()
provider = TracerProvider()
provider.add_span_processor(spans)
trace.set_tracer_provider(provider)


@pytest.fixture
def tracer_spans():
    """Setup tracer and return span collector"""
    yield spans
    spans.spans = []


@pytest.fixture
def test_schema():
    return """
    type Query {
        syncField: String
        asyncField: String
        errorField: String
        errorAsyncField: String
        optionalArg(name: String): String
        requiredArg(name: String!): String
    }
    type Subscription {
        countdown(from_: Int!): Int!
    }
    """


@pytest.mark.asyncio
async def test_sync_resolver(tracer_spans, test_schema):
    """Test tracing of synchronous resolver"""
    api = create_instrumented_api(schema=test_schema)

    @api.query(field_name="syncField")
    def syncField(parent, info):
        return "sync result"

    result = await api.call(
        """
        query {
            syncField
        }
    """
    )

    assert result.data == {"syncField": "sync result"}
    assert not result.errors

    # Find the resolver span
    resolver_span = next(
        span for span in tracer_spans.spans if span.name == "graphql.resolve.syncField"
    )

    assert resolver_span.attributes["graphql.field"] == "syncField"
    assert resolver_span.attributes["graphql.parent_type"] == "Query"
    assert resolver_span.attributes["graphql.return_type"] == "String"
    assert resolver_span.status.status_code == StatusCode.UNSET


@pytest.mark.asyncio
async def test_async_resolver(tracer_spans, test_schema):
    """Test tracing of asynchronous resolver"""
    api = create_instrumented_api(schema=test_schema)

    @api.query(field_name="asyncField")
    async def asyncField(parent, info):
        return "async result"

    result = await api.call(
        """
        query {
            asyncField
        }
    """
    )

    assert result.data == {"asyncField": "async result"}
    assert not result.errors

    # Find the resolver span
    resolver_span = next(
        span for span in tracer_spans.spans if span.name == "graphql.resolve.asyncField"
    )

    assert resolver_span.attributes["graphql.field"] == "asyncField"
    assert resolver_span.attributes["graphql.parent_type"] == "Query"
    assert resolver_span.attributes["graphql.return_type"] == "String"
    assert resolver_span.status.status_code == StatusCode.UNSET


@pytest.mark.asyncio
async def test_resolver_error(tracer_spans, test_schema):
    """Test tracing of resolver that raises an error"""
    api = create_instrumented_api(schema=test_schema)

    @api.query(field_name="errorField")
    def errorField(parent, info):
        raise ValueError("test error")

    @api.query(field_name="errorAsyncField")
    async def errorAsyncField(parent, info):
        raise ValueError("test async error")

    result = await api.call(
        """
        query {
            errorField
            errorAsyncField
        }
    """
    )

    assert result.data == {"errorField": None, "errorAsyncField": None}
    assert result.errors is not None

    # Find the resolver span
    resolver_span = next(
        span for span in tracer_spans.spans if span.name == "graphql.resolve.errorField"
    )

    assert resolver_span.status.status_code == StatusCode.ERROR
    # events will contain the exception data
    error_event = next(
        event for event in resolver_span.events if event.name == "exception"
    )
    assert "test error" in error_event.attributes["exception.message"]

    # Find the async resolver span
    async_resolver_span = next(
        span
        for span in tracer_spans.spans
        if span.name == "graphql.resolve.errorAsyncField"
    )

    assert async_resolver_span.status.status_code == StatusCode.ERROR
    # events will contain the exception data
    error_event = next(
        event for event in async_resolver_span.events if event.name == "exception"
    )
    assert "test async error" in error_event.attributes["exception.message"]


@pytest.mark.asyncio
async def test_resolver_with_args(tracer_spans, test_schema):
    """Test tracing of resolver with arguments"""
    api = create_instrumented_api(schema=test_schema)

    @api.query(field_name="optionalArg")
    def optionalArg(parent, info, name=None):
        return f"Hello, {name or 'World'}"

    @api.query(field_name="requiredArg")
    def requiredArg(parent, info, name):
        return f"Hello, {name}"

    # Test optional arg
    result = await api.call(
        """
        query {
            withoutArg: optionalArg
            withArg: optionalArg(name: "Test")
        }
    """
    )

    assert result.data == {"withoutArg": "Hello, World", "withArg": "Hello, Test"}

    # Test required arg
    result = await api.call(
        """
        query {
            requiredArg(name: "Required")
        }
    """
    )

    assert result.data == {"requiredArg": "Hello, Required"}

    # Verify all resolver spans were created
    resolver_spans = [
        span for span in tracer_spans.spans if span.name.startswith("graphql.resolve.")
    ]
    assert len(resolver_spans) == 3  # Two optionalArg calls and one requiredArg


@pytest.mark.asyncio
async def test_multiple_resolvers_same_query(tracer_spans, test_schema):
    """Test tracing of multiple resolvers in a single query"""
    api = create_instrumented_api(schema=test_schema)

    @api.query(field_name="syncField")
    def syncField(parent, info):
        return "sync"

    @api.query(field_name="asyncField")
    async def asyncField(parent, info):
        return "async"

    result = await api.call(
        """
        query {
            syncField
            asyncField
        }
    """
    )

    assert result.data == {"syncField": "sync", "asyncField": "async"}

    # Verify both resolver spans were created
    resolver_spans = [
        span for span in tracer_spans.spans if span.name.startswith("graphql.resolve.")
    ]
    assert len(resolver_spans) == 2

    span_names = {span.name for span in resolver_spans}
    assert "graphql.resolve.syncField" in span_names
    assert "graphql.resolve.asyncField" in span_names


class AsyncRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.start > self.end:
            await asyncio.sleep(0.001)
            value = self.start
            self.start -= 1
            return value
        else:
            raise StopAsyncIteration


async def countdown(info, from_: int) -> AsyncIterable[dict]:
    async for i in AsyncRange(from_, -1):
        yield {"countdown": i}


async def test_subscriptions(tracer_spans, test_schema):
    """Test tracing of multiple resolvers in a single query"""
    api = create_instrumented_api(
        schema=test_schema, root_value={"countdown": countdown}
    )

    result = await api.subscribe(
        """
            subscription Subby{
                countdown(from_: 5)
            }
        """,
        operation_name="Subby",
    )

    assert result is not None
    assert isinstance(result, AsyncIterable)
    async for d in result:
        print(d)

    assert len(tracer_spans.spans) == 3
    subscribe_span = next(
        span for span in tracer_spans.spans if span.name == "graphql.subscribe"
    )

    assert subscribe_span.attributes["graphql.operation_name"] == "Subby"
    assert subscribe_span.status.status_code == StatusCode.UNSET


async def test_validation_errors(tracer_spans, test_schema):
    api = create_instrumented_api(schema=test_schema)

    result = await api.call(
        """
        query {
            asyncField(arg: "invalid")
        }
    """
    )
    assert result.errors is not None

    validate_span = next(
        span for span in tracer_spans.spans if span.name == "graphql.validation"
    )
    assert validate_span.status.status_code == StatusCode.ERROR
    # events will contain the exception data
    error_event = next(
        event for event in validate_span.events if event.name == "exception"
    )
    assert (
        "Unknown argument 'arg' on field 'Query.asyncField'"
        in error_event.attributes["exception.message"]
    )


async def test_parser_errors(tracer_spans, test_schema):
    api = create_instrumented_api(schema=test_schema)

    result = await api.call("query {")
    assert result.errors is not None

    parse_span = next(
        span for span in tracer_spans.spans if span.name == "graphql.parse.document"
    )
    assert parse_span.attributes["graphql.document"] == "query {"
    assert parse_span.status.status_code == StatusCode.ERROR
    # events will contain the exception data
    error_event = next(
        event for event in parse_span.events if event.name == "exception"
    )
    assert "Syntax Error: Expected Name" in error_event.attributes["exception.message"]
