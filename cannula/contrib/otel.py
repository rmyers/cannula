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

from typing import AsyncIterable, List, Dict, Any, Callable, Mapping

from graphql import (
    DocumentNode,
    ExecutionResult,
    GraphQLError,
    GraphQLObjectType,
    GraphQLResolveInfo,
)
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from cannula.api import CannulaAPI, ParseResults

TRACER = trace.get_tracer("cannula")


def resolve_name(func: Callable) -> str:
    """Return a string with the dotted path of the function"""
    klass = func.__class__.__name__
    func_name = func.__qualname__
    resolver = func_name if klass == "function" else f"{klass}.{func_name}"
    return f"{func.__module__}.{resolver}"


def trace_field_resolver(
    source: GraphQLObjectType,
    info: GraphQLResolveInfo,
    **kwargs,
):
    """Defualt field resolver that wraps callables in spans.

    Typically the fields are simple attributes and these do not
    matter for tracing and in fact may slow down processing since
    they are so common.

    This resolver will instead just add spans and attributes for
    anything that is callable.
    """
    field_name = info.field_name
    value = (
        source.get(field_name)
        if isinstance(source, Mapping)
        else getattr(source, field_name, None)
    )
    if callable(value):
        with TRACER.start_span(
            f"graphql.resolve.{field_name}",
            attributes={
                "graphql.field": field_name,
                "graphql.parent_type": info.parent_type.name,
                "graphql.return_type": str(info.return_type),
                "graphql.resolve_function": resolve_name(value),
            },
        ) as span:
            try:
                return value(info, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR))
                raise
    return value


def trace_middleware(
    next_fn: Callable[..., Any],
    parent_object: GraphQLObjectType,
    info: GraphQLResolveInfo,
    **kwargs,
):
    """Trace resolver functions middleware.

    This will add spans to any resolvers that are callable.

    Usage::

        api = create_instrumented_api(
            schema="...",
            middleware=[trace_middleware]
        )

    """
    function_name = next_fn.__name__
    field_name = info.field_name
    parent_name = info.parent_type.name

    if parent_name.startswith("__"):
        return next_fn(parent_object, info, **kwargs)

    if field_name.startswith("__"):
        return next_fn(parent_object, info, **kwargs)

    if function_name == "default_field_resolver":
        return trace_field_resolver(parent_object, info, **kwargs)

    with TRACER.start_span(
        f"graphql.resolve.{field_name}",
        attributes={
            "graphql.field": field_name,
            "graphql.parent_type": parent_name,
            "graphql.return_type": str(info.return_type),
            "graphql.resolver_function": resolve_name(next_fn),
        },
    ) as span:
        try:
            return next_fn(parent_object, info, **kwargs)
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            raise


class InstrumentedCannulaAPI(CannulaAPI):

    def validate(self, document: DocumentNode) -> List[GraphQLError]:
        with TRACER.start_span("graphql.validation") as span:
            errors = super().validate(document)
            for error in errors:
                span.record_exception(error)
                span.set_status(Status(StatusCode.ERROR))
            return errors

    def parse_document(self, document: str) -> ParseResults:
        with TRACER.start_span("graphql.parse.document") as span:
            span.set_attribute("graphql.document", document)
            parsed_results = super().parse_document(document)
            for error in parsed_results.errors:
                span.record_exception(error)
                span.set_status(Status(StatusCode.ERROR))
            return parsed_results

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
