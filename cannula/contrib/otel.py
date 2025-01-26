"""
OpenTelemetry Integration
=========================

This package provides OpenTelemetry instrumentation for CannulaAPI, enabling detailed tracing of GraphQL operations including parsing, validation, and execution phases.

Installation
--------------

.. code-block:: bash

    pip install opentelemetry-api opentelemetry-sdk


Basic Usage
-----------

Here's a simple example of how to instrument your CannulaAPI application:

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

    # Initialize OpenTelemetry
    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Create and instrument your API
    api = CannulaAPI(schema="...")
    instrument_cannula(api)


Generated Spans
---------------

The instrumentation creates the following spans for each GraphQL operation:

1. `graphql.request` (Parent span) Attributes:

    - `graphql.operation.name`: Name of the operation if provided
    - `graphql.document`: The GraphQL query string

2. `graphql.parse` (Child span)

    - Created when parsing string queries
    - Records parsing errors if they occur

3. `graphql.validate` (Child span)

    - Records validation errors if they occur

4. `graphql.execute` (Child span) Attributes:

    - `graphql.response.size`: Size of the response data
    - Records execution errors if they occur

Error Handling
--------------

All spans automatically capture errors with appropriate status codes:

* Parsing errors are captured in the parse span
* Validation errors are captured in the validate span
* Execution errors are captured in the execute span
* Unexpected errors are captured in the main request span

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

    api = CannulaAPI(
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

    api = CannulaAPI(
        schema="...",
        middleware=[custom_middleware]
    )


Testing
-------

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
~~~~~~~~~~~~~~

1. Use BatchSpanProcessor in production for better performance
2. Configure appropriate sampling rates for high-traffic services
3. Add relevant business context to spans via middleware
4. Monitor the overhead of tracing in your application
5. Consider using sampling in production environments

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

The OpenTelemetry instrumentation adds minimal overhead to your application. However, consider the following:

* Use BatchSpanProcessor instead of SimpleSpanProcessor in production
* Configure appropriate sampling rates for high-traffic services
* Monitor the memory usage of your span processors
* Configure appropriate flush intervals for batch processors
"""

from functools import wraps
from typing import Optional, Dict, Any, Union

from graphql import DocumentNode, ExecutionResult
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

import cannula


def instrument_cannula(api_instance: "cannula.CannulaAPI") -> None:
    """
    Instruments a CannulaAPI instance with OpenTelemetry tracing.

    Args:
        api_instance: The CannulaAPI instance to instrument
    """
    tracer = trace.get_tracer("cannula.graphql")
    original_call = api_instance.call

    @wraps(original_call)
    async def wrapped_call(
        document: Union[DocumentNode, str],
        *,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        context: Optional[Any] = None,
        request: Optional[Any] = None,
    ) -> ExecutionResult:
        with tracer.start_as_current_span(
            name="graphql.request",
            kind=trace.SpanKind.SERVER,
        ) as span:
            # Set basic span attributes
            if operation_name:
                span.set_attribute("graphql.operation.name", operation_name)

            # Record the query as span attribute
            if isinstance(document, str):
                span.set_attribute("graphql.document", document)

            # Create child span for parsing if needed
            if isinstance(document, str):
                with tracer.start_span("graphql.parse") as parse_span:
                    parse_result = api_instance._parse_document(document)
                    if parse_result.errors:
                        parse_span.set_status(Status(StatusCode.ERROR))
                        parse_span.record_exception(parse_result.errors[0])
                        return ExecutionResult(data=None, errors=parse_result.errors)
                    document = parse_result.document_ast

            # Create child span for validation
            with tracer.start_span("graphql.validate") as validate_span:
                validation_errors = api_instance._validate(document)
                if validation_errors:
                    validate_span.set_status(Status(StatusCode.ERROR))
                    validate_span.record_exception(validation_errors[0])
                    return ExecutionResult(data=None, errors=validation_errors)

            try:
                # Execute the query
                with tracer.start_span("graphql.execute") as execute_span:
                    result = await original_call(
                        document=document,
                        variables=variables,
                        operation_name=operation_name,
                        context=context,
                        request=request,
                    )

                    if result.errors:
                        execute_span.set_status(Status(StatusCode.ERROR))
                        for error in result.errors:
                            execute_span.record_exception(error)

                    # Add response size metrics
                    if result.data:
                        execute_span.set_attribute(
                            "graphql.response.size", len(str(result.data))
                        )

                    return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise

    # Replace the original call method with our wrapped version
    api_instance.call = wrapped_call  # type: ignore
