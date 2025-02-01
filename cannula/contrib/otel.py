"""
OpenTelemetry Integration
=========================

This package provides OpenTelemetry instrumentation for CannulaAPI, enabling detailed
tracing of GraphQL operations including parsing, validation, and execution phases.

Installation
------------

.. code-block:: bash

    pip install opentelemetry-api opentelemetry-sdk


Basic Usage
-----------

There are two ways to use the instrumentation:

1. Using the Factory Function (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

    # Initialize OpenTelemetry
    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Create an instrumented API
    api = create_instrumented_api(schema="type Query { hello: String }")

2. Using the Class Directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Create an instrumented API using the class
    api = InstrumentedCannulaAPI(schema="type Query { hello: String }")

Type Safety
~~~~~~~~~~~

The instrumented API maintains full type safety with your root types:

.. code-block:: python

    from typing import TypedDict

    class MyRootType(TypedDict, total=False):
        hello: str

    # Type-safe instrumented API
    api = create_instrumented_api[MyRootType](
        schema="type Query { hello: String }",
        root_value={"hello": "world"}
    )


Generated Spans
---------------

The instrumentation creates the following spans for each GraphQL operation:

1. ``graphql.execute`` (Parent span)
    - Attributes:
        - ``graphql.operation_name``: Name of the operation if provided, "anonymous" otherwise
        - ``graphql.context``: String representation of the context
        - ``graphql.response.size``: Size of the response data (if available)

2. ``graphql.parse.document`` (Child span)
    - Created when parsing string queries
    - Attributes:
        - ``graphql.document``: The GraphQL query string
    - Records parsing errors if they occur

3. ``graphql.validation`` (Child span)
    - Records validation errors if they occur

4. ``graphql.subscribe`` (Subscription span)
    - Attributes:
        - ``graphql.operation_name``: Name of the operation if provided, "anonymous" otherwise
        - ``graphql.context``: String representation of the context


Error Handling
--------------

All spans automatically capture errors with appropriate status codes:

* Parsing errors are captured in the parse span
* Validation errors are captured in the validate span
* Execution errors are captured in the execute span
* All errors are recorded using ``span.record_exception()`` and set appropriate error status


Integration with Other Exporters
--------------------------------

You can use any OpenTelemetry exporter. Here are some common examples:

Jaeger
~~~~~~

.. code-block:: python

    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))


OTLP (OpenTelemetry Protocol)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    otlp_exporter = OTLPSpanExporter(
        endpoint="your-otlp-endpoint:4317",
        insecure=True
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))


Advanced Configuration
----------------------

Custom Context
~~~~~~~~~~~~~~

The instrumentation will automatically include any context from your CannulaAPI context class:

.. code-block:: python

    class MyContext(Context):
        def __init__(self, request):
            self.user_id = request.headers.get('X-User-Id')
            self.tenant_id = request.headers.get('X-Tenant-Id')

    api = InstrumentedCannulaAPI(
        schema="...",
        context=MyContext
    )

Adding Custom Attributes
~~~~~~~~~~~~~~~~~~~~~~~~

You can extend the instrumentation by adding custom middleware that adds attributes to the spans:

.. code-block:: python

    from opentelemetry import trace

    async def custom_middleware(resolve, root, info, **args):
        current_span = trace.get_current_span()
        current_span.set_attribute("custom.attribute", "value")
        return await resolve(root, info, **args)

    api = InstrumentedCannulaAPI(
        schema="...",
        middleware=[custom_middleware]
    )


Testing
--------

When testing instrumented code, you can use the provided test utilities:

.. code-block:: python

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    # Setup test provider
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    # Your tests...


Best Practices
--------------

1. Use BatchSpanProcessor in production for better performance
2. Configure appropriate sampling rates for high-traffic services
3. Add relevant business context to spans via middleware
4. Monitor the overhead of tracing in your application
5. Consider using sampling in production environments

Performance Considerations
--------------------------

The OpenTelemetry instrumentation adds minimal overhead to your application. However, consider the following:

* Use BatchSpanProcessor instead of SimpleSpanProcessor in production
* Configure appropriate sampling rates for high-traffic services
* Monitor the memory usage of your span processors
* Configure appropriate flush intervals for batch processors
"""

from functools import wraps
from inspect import iscoroutinefunction
from typing import AsyncIterable, List, Dict, Any, Callable

from graphql import (
    DocumentNode,
    ExecutionResult,
    GraphQLError,
)
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from cannula.api import CannulaAPI, ParseResults

TRACER = trace.get_tracer("cannula")


def trace_resolver(resolver: Callable) -> Callable:
    """Wraps a resolver function to add tracing."""

    @wraps(resolver)
    async def async_wrapper(parent, info, **kwargs):
        with TRACER.start_span(
            f"graphql.resolve.{info.field_name}",
            attributes={
                "graphql.field": info.field_name,
                "graphql.parent_type": info.parent_type.name,
                "graphql.return_type": info.return_type.name,
            },
        ) as span:
            try:
                return await resolver(parent, info, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR))
                raise

    @wraps(resolver)
    def sync_wrapper(parent, info, **kwargs):
        with TRACER.start_span(
            f"graphql.resolve.{info.field_name}",
            attributes={
                "graphql.field": info.field_name,
                "graphql.parent_type": info.parent_type.name,
                "graphql.return_type": info.return_type.name,
            },
        ) as span:
            try:
                return resolver(parent, info, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR))
                raise

    return async_wrapper if iscoroutinefunction(resolver) else sync_wrapper


class InstrumentedCannulaAPI(CannulaAPI):

    def _validate(self, document: DocumentNode) -> List[GraphQLError]:
        with TRACER.start_span("graphql.validation") as span:
            errors = super()._validate(document)
            for error in errors:
                span.record_exception(error)
                span.set_status(Status(StatusCode.ERROR))
            return errors

    def _parse_document(self, document: str) -> ParseResults:
        with TRACER.start_span("graphql.parse.document") as span:
            span.set_attribute("graphql.document", document)
            parsed_results = super()._parse_document(document)
            for error in parsed_results.errors:
                span.record_exception(error)
                span.set_status(Status(StatusCode.ERROR))
            return parsed_results

    def resolver(self, type_name: str, field_name: str | None = None):
        """Override resolver decorator to add tracing."""
        original_decorator = super().resolver(type_name, field_name)

        def wrapper(func):
            traced_resolver = trace_resolver(func)
            return original_decorator(traced_resolver)

        return wrapper

    async def call(
        self,
        document: DocumentNode | str,
        *,
        variables: Dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: Any | None = None,
        request: Any | None = None,
    ) -> ExecutionResult:
        with TRACER.start_as_current_span("graphql.execute") as span:
            span.set_attribute("graphql.operation_name", operation_name or "anonymous")
            span.set_attribute("graphql.context", str(context))

            results = await super().call(
                document,
                variables=variables,
                operation_name=operation_name,
                context=context,
                request=request,
            )

            if results.data:
                span.set_attribute("graphql.response.size", len(str(results.data)))

            if results.errors is not None:
                for error in results.errors:
                    span.record_exception(error)
                    span.set_status(Status(StatusCode.ERROR))

            return results

    async def subscribe(
        self,
        document: DocumentNode | str,
        *,
        variables: Dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: Any | None = None,
        request: Any | None = None,
    ) -> AsyncIterable[ExecutionResult] | ExecutionResult:
        with TRACER.start_as_current_span("graphql.subscribe") as span:
            span.set_attribute("graphql.operation_name", operation_name or "anonymous")
            span.set_attribute("graphql.context", str(context))
            return await super().subscribe(
                document,
                variables=variables,
                operation_name=operation_name,
                context=context,
                request=request,
            )


def create_instrumented_api(*args, **kwargs) -> InstrumentedCannulaAPI:
    """
    Factory function to create an instrumented CannulaAPI instance.
    This provides a more convenient way to create an instrumented API
    without explicitly using the class.

    Usage:
        api = create_instrumented_api(schema="type Query { hello: String }")
    """
    return InstrumentedCannulaAPI(*args, **kwargs)
