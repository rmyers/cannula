"""
Request/Response Tracker using contextvars

This module provides a way to track HTTP requests and responses using contextvars,
which can be collected for debugging purposes in GraphQL responses.
"""

import contextlib
import contextvars
import time
import typing

from dataclasses import dataclass, field

from graphql import ExecutionResult


@dataclass
class HttpTransaction:
    """Complete HTTP transaction record"""

    # Request info
    method: str
    url: str
    request_headers: typing.Dict[str, str]
    request_body: typing.Optional[typing.Any] = None

    # Response info
    response_status: typing.Optional[int] = None
    response_headers: typing.Optional[typing.Dict[str, str]] = None
    response_body: typing.Optional[typing.Any] = None

    # Timing and error info
    start_time: float = field(default_factory=time.time)
    end_time: typing.Optional[float] = None
    error: typing.Optional[str] = None

    @property
    def duration_ms(self) -> typing.Optional[float]:
        """Calculate request duration in milliseconds"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """Convert to a dictionary for GraphQL extensions"""
        result = {
            "method": self.method,
            "url": self.url,
            "requestHeaders": self.request_headers,
            "startTime": self.start_time,
        }

        if self.request_body is not None:
            result["requestBody"] = self.request_body

        if self.response_status is not None:
            result["responseStatus"] = self.response_status
            result["responseHeaders"] = self.response_headers
            result["responseBody"] = self.response_body
            result["endTime"] = self.end_time
            result["durationMs"] = self.duration_ms

        if self.error is not None:
            result["error"] = self.error
            result["endTime"] = self.end_time
            result["durationMs"] = self.duration_ms

        return result


# Contextvar for storing HTTP transactions
http_transactions = contextvars.ContextVar("http_transactions", default=[])


def record_transaction(transaction: HttpTransaction) -> None:
    """Record a complete HTTP transaction"""
    current = http_transactions.get()
    current.append(transaction)
    http_transactions.set(current)


def get_transactions() -> typing.List[HttpTransaction]:
    """Get all recorded HTTP transactions"""
    return http_transactions.get()


def reset_transactions() -> None:
    """Reset the transaction list"""
    http_transactions.set([])


def collect_transaction_data() -> typing.List[typing.Dict[str, typing.Any]]:
    """Collect all transaction data as dictionaries for GraphQL extensions"""
    return [transaction.to_dict() for transaction in get_transactions()]


class TrackingSession:
    """
    Session that tracks HTTP requests for GraphQL operations
    """

    def __init__(self, debug: bool = False):
        """Initialize a tracking session"""
        self.debug = debug
        self.start_time = time.time()
        # Always reset tracking for this context
        reset_transactions()

    def enhance_result(self, result: ExecutionResult) -> ExecutionResult:
        """
        Add tracking information to GraphQL result if debug is enabled
        """
        if not self.debug:
            return result

        # Calculate execution time
        execution_time = (time.time() - self.start_time) * 1000  # ms

        # Initialize extensions if needed
        if result.extensions is None:
            result.extensions = {}

        # Add debug information to extensions
        result.extensions["debug"] = {
            "executionTimeMs": execution_time,
            "httpRequests": collect_transaction_data(),
        }

        return result


@contextlib.asynccontextmanager
async def tracking_session(debug: bool = False):
    """Context manager that provides a tracking session"""
    session = TrackingSession(debug=debug)
    try:
        yield session
    finally:
        pass
