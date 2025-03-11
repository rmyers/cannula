"""
Request/Response Tracker using contextvars

This module provides a way to track HTTP requests and responses using contextvars,
which can be collected for debugging purposes in GraphQL responses.
"""

import contextlib
import contextvars
import time
import typing
from types import TracebackType
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


# Create a Token class for the context var to ensure proper scoping
class TransactionContextToken:
    """Token class for managing transaction context"""

    def __init__(self, transactions: typing.List[HttpTransaction]):
        self.transactions = transactions


# Contextvar for storing HTTP transactions with an empty default
# The default is None, so we know when to initialize a new context
http_transaction_ctx: contextvars.ContextVar[
    typing.Optional[TransactionContextToken]
] = contextvars.ContextVar("http_transaction_ctx", default=None)


def record_transaction(transaction: HttpTransaction) -> None:
    """
    Record a complete HTTP transaction in the current context.
    This is a no-op if no tracking session is active.
    """
    ctx_token: typing.Optional[TransactionContextToken] = http_transaction_ctx.get()

    # Skip recording if no context exists
    if ctx_token is None:
        return

    # Add transaction to the current context
    ctx_token.transactions.append(transaction)


def get_transactions() -> typing.List[HttpTransaction]:
    """Get all recorded HTTP transactions from the current context"""
    ctx_token: typing.Optional[TransactionContextToken] = http_transaction_ctx.get()
    return ctx_token.transactions if ctx_token is not None else []


def collect_transaction_data() -> typing.List[typing.Dict[str, typing.Any]]:
    """Collect all transaction data as dictionaries for GraphQL extensions"""
    return [transaction.to_dict() for transaction in get_transactions()]


class TrackingSession:
    """
    Session that tracks HTTP requests for GraphQL operations
    """

    def __init__(self, debug: bool = False):
        """Initialize a tracking session with a fresh context"""
        self.debug: bool = debug
        self.start_time: float = time.time()
        # Create a new context for this session
        self.token: TransactionContextToken = TransactionContextToken([])
        self.context_token: contextvars.Token = http_transaction_ctx.set(self.token)

    def __enter__(self) -> "TrackingSession":
        """Support context manager protocol"""
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_val: typing.Optional[BaseException],
        exc_tb: typing.Optional[TracebackType],
    ) -> None:
        """Reset context on exit"""
        http_transaction_ctx.reset(self.context_token)

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
async def tracking_session(
    debug: bool = False,
) -> typing.AsyncGenerator[TrackingSession, None]:
    """Context manager that provides a tracking session with automatic cleanup"""
    session = TrackingSession(debug=debug)
    token: contextvars.Token = session.context_token
    try:
        yield session
    finally:
        # Ensure the context is reset even if there's an exception
        http_transaction_ctx.reset(token)
