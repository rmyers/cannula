"""
Tests for the HTTP transaction tracking module.
"""

import time

from graphql import ExecutionResult

from cannula.tracking import (
    HttpTransaction,
    TransactionContextToken,
    http_transaction_ctx,
    record_transaction,
    get_transactions,
    collect_transaction_data,
    TrackingSession,
    tracking_session,
)


class TestHttpTransaction:
    """Test the HttpTransaction dataclass"""

    def test_duration_calculation(self):
        """Test duration calculation when end time is set"""
        transaction = HttpTransaction(
            method="GET",
            url="https://example.com",
            request_headers={},
            start_time=1000.0,
            end_time=1001.0,
        )
        assert transaction.duration_ms == 1000.0  # 1 second = 1000ms

    def test_duration_none_when_no_end_time(self):
        """Test duration is None when end_time is not set"""
        transaction = HttpTransaction(
            method="GET",
            url="https://example.com",
            request_headers={},
            start_time=1000.0,
        )
        assert transaction.duration_ms is None

    def test_to_dict_basic_fields(self):
        """Test to_dict() includes basic fields"""
        transaction = HttpTransaction(
            method="GET",
            url="https://example.com",
            request_headers={"User-Agent": "Test"},
            start_time=1000.0,
        )
        result = transaction.to_dict()
        assert result["method"] == "GET"
        assert result["url"] == "https://example.com"
        assert result["requestHeaders"] == {"User-Agent": "Test"}
        assert result["startTime"] == 1000.0
        assert "requestBody" not in result

    def test_to_dict_with_request_body(self):
        """Test to_dict() includes request body when present"""
        transaction = HttpTransaction(
            method="POST",
            url="https://example.com",
            request_headers={},
            request_body={"test": "data"},
        )
        result = transaction.to_dict()
        assert result["requestBody"] == {"test": "data"}

    def test_to_dict_with_response(self):
        """Test to_dict() includes response data when present"""
        transaction = HttpTransaction(
            method="GET",
            url="https://example.com",
            request_headers={},
            response_status=200,
            response_headers={"Content-Type": "application/json"},
            response_body={"result": "success"},
            start_time=1000.0,
            end_time=1001.0,
        )
        result = transaction.to_dict()
        assert result["responseStatus"] == 200
        assert result["responseHeaders"] == {"Content-Type": "application/json"}
        assert result["responseBody"] == {"result": "success"}
        assert result["endTime"] == 1001.0
        assert result["durationMs"] == 1000.0

    def test_to_dict_with_error(self):
        """Test to_dict() includes error when present"""
        transaction = HttpTransaction(
            method="GET",
            url="https://example.com",
            request_headers={},
            error="Connection timeout",
            start_time=1000.0,
            end_time=1001.0,
        )
        result = transaction.to_dict()
        assert result["error"] == "Connection timeout"
        assert result["endTime"] == 1001.0
        assert result["durationMs"] == 1000.0


class TestContextManagement:
    """Test context management for HTTP transactions"""

    def test_no_tracking_by_default(self):
        """Test that no tracking context exists by default"""
        assert http_transaction_ctx.get() is None

    def test_record_transaction_no_context(self):
        """Test recording a transaction with no context is a no-op"""
        # Ensure no context exists
        http_transaction_ctx.set(None)

        # Record a transaction
        transaction = HttpTransaction(
            method="GET", url="https://example.com", request_headers={}
        )
        record_transaction(transaction)

        # Verify no transactions are returned
        assert get_transactions() == []

    def test_get_transactions_no_context(self):
        """Test get_transactions returns empty list when no context exists"""
        # Ensure no context exists
        http_transaction_ctx.set(None)

        # Verify no transactions are returned
        assert get_transactions() == []

    def test_manual_context_management(self):
        """Test manually creating and managing a context"""
        # Create a context token
        token = TransactionContextToken([])
        ctx_token = http_transaction_ctx.set(token)

        try:
            # Record a transaction
            transaction = HttpTransaction(
                method="GET", url="https://example.com", request_headers={}
            )
            record_transaction(transaction)

            # Verify the transaction was recorded
            assert len(get_transactions()) == 1
            assert get_transactions()[0] == transaction
        finally:
            # Reset the context
            http_transaction_ctx.reset(ctx_token)

        # Verify context is cleared
        assert http_transaction_ctx.get() is None


class TestTrackingSession:
    """Test the TrackingSession class"""

    def test_init_creates_context(self):
        """Test that initializing a session creates a context"""
        session = TrackingSession()
        try:
            http_transactions = http_transaction_ctx.get()
            assert http_transactions is not None
            assert isinstance(http_transactions, TransactionContextToken)
            assert http_transactions.transactions == []
        finally:
            http_transaction_ctx.reset(session.context_token)

    def test_context_manager(self):
        """Test using TrackingSession as a context manager"""
        # Before entering context
        assert http_transaction_ctx.get() is None

        # Use with block to ensure both __enter__ and __exit__ are called
        with TrackingSession() as session:
            assert http_transaction_ctx.get() is not None
            assert isinstance(session, TrackingSession)

        # Context should be reset after exiting the with block
        assert http_transaction_ctx.get() is None

    def test_recording_in_session(self):
        """Test recording transactions in a session"""
        with TrackingSession() as session:
            assert session is not None
            # Record transactions
            transaction1 = HttpTransaction(
                method="GET", url="https://example.com/1", request_headers={}
            )
            transaction2 = HttpTransaction(
                method="POST", url="https://example.com/2", request_headers={}
            )

            record_transaction(transaction1)
            record_transaction(transaction2)

            # Verify transactions were recorded
            transactions = get_transactions()
            assert len(transactions) == 2
            assert transactions[0] == transaction1
            assert transactions[1] == transaction2

        # Context should be reset after session ends
        assert http_transaction_ctx.get() is None

        # No transactions should exist outside the session
        assert get_transactions() == []

    def test_enhance_result_debug_false(self):
        """Test enhance_result with debug=False doesn't modify result"""
        session = TrackingSession(debug=False)
        try:
            # Create a mock result
            result = ExecutionResult(data={"test": "data"})

            # Enhance the result
            enhanced = session.enhance_result(result)

            # Verify result wasn't modified
            assert enhanced.extensions is None
        finally:
            http_transaction_ctx.reset(session.context_token)

    def test_enhance_result_debug_true(self):
        """Test enhance_result with debug=True adds debug info"""
        session = TrackingSession(debug=True)
        try:
            # Record a transaction
            transaction = HttpTransaction(
                method="GET",
                url="https://example.com",
                request_headers={},
                response_status=200,
                response_headers={},
                response_body={"result": "success"},
                end_time=time.time(),
            )
            record_transaction(transaction)

            # Create a mock result
            result = ExecutionResult(data={"test": "data"})

            # Enhance the result
            enhanced = session.enhance_result(result)

            # Verify debug info was added
            assert enhanced.extensions is not None
            assert "debug" in enhanced.extensions
            assert "executionTimeMs" in enhanced.extensions["debug"]
            assert "httpRequests" in enhanced.extensions["debug"]
            assert len(enhanced.extensions["debug"]["httpRequests"]) == 1
        finally:
            http_transaction_ctx.reset(session.context_token)


class TestAsyncTracking:
    """Test async tracking session context manager"""

    async def test_async_context_manager(self):
        """Test async context manager creates and cleans up context"""
        async with tracking_session() as session:
            assert http_transaction_ctx.get() is not None
            assert isinstance(session, TrackingSession)

            # Record a transaction
            transaction = HttpTransaction(
                method="GET", url="https://example.com", request_headers={}
            )
            record_transaction(transaction)

            # Verify transaction was recorded
            assert len(get_transactions()) == 1

        # Context should be reset after exiting
        assert http_transaction_ctx.get() is None

    async def test_async_context_manager_exception(self):
        """Test async context manager cleans up even if exception occurs"""
        try:
            async with tracking_session() as session:
                assert session is not None
                assert http_transaction_ctx.get() is not None

                # Record a transaction
                transaction = HttpTransaction(
                    method="GET", url="https://example.com", request_headers={}
                )
                record_transaction(transaction)

                # Raise an exception
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Context should be reset after exiting, even with exception
        assert http_transaction_ctx.get() is None

    async def test_nested_sessions(self):
        """Test behavior with nested tracking sessions"""
        async with tracking_session() as outer_session:
            assert outer_session is not None
            # Record in outer session
            outer_transaction = HttpTransaction(
                method="GET", url="https://outer.com", request_headers={}
            )
            record_transaction(outer_transaction)

            async with tracking_session() as inner_session:
                assert inner_session is not None
                # Inner session should create its own context
                inner_transaction = HttpTransaction(
                    method="GET", url="https://inner.com", request_headers={}
                )
                record_transaction(inner_transaction)

                # Inner session should only have inner transaction
                inner_transactions = get_transactions()
                assert len(inner_transactions) == 1
                assert inner_transactions[0].url == "https://inner.com"

            # After inner session, outer session should be restored
            outer_transactions = get_transactions()
            assert len(outer_transactions) == 1
            assert outer_transactions[0].url == "https://outer.com"

        # Both sessions should be cleaned up
        assert http_transaction_ctx.get() is None


class TestCollectionFunctions:
    """Test collection functions"""

    def test_collect_transaction_data(self):
        """Test collect_transaction_data converts transactions to dicts"""
        with TrackingSession():
            # Record transactions
            transaction1 = HttpTransaction(
                method="GET",
                url="https://example.com/1",
                request_headers={},
                response_status=200,
                response_headers={},
                response_body={"result": "success"},
                start_time=1000.0,
                end_time=1001.0,
            )
            transaction2 = HttpTransaction(
                method="POST",
                url="https://example.com/2",
                request_headers={},
                request_body={"data": "test"},
                error="Failed",
                start_time=1002.0,
                end_time=1003.0,
            )

            record_transaction(transaction1)
            record_transaction(transaction2)

            # Collect data
            data = collect_transaction_data()

            # Verify data was collected correctly
            assert len(data) == 2
            assert data[0]["method"] == "GET"
            assert data[0]["url"] == "https://example.com/1"
            assert data[0]["responseStatus"] == 200
            assert data[0]["durationMs"] == 1000.0

            assert data[1]["method"] == "POST"
            assert data[1]["url"] == "https://example.com/2"
            assert data[1]["requestBody"] == {"data": "test"}
            assert data[1]["error"] == "Failed"
            assert data[1]["durationMs"] == 1000.0
