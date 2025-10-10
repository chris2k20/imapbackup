"""
Tests for retry logic and network error handling
"""
import pytest
import socket
import imaplib
import time
from unittest.mock import Mock, patch
import imapbackup


@pytest.mark.unit
class TestRetryLogic:
    """Tests for retry_on_network_error function"""

    def test_retry_success_on_first_attempt(self):
        """Test successful operation on first attempt"""
        call_count = []

        def successful_operation():
            call_count.append(1)
            return "success"

        result = imapbackup.retry_on_network_error(successful_operation)

        assert result == "success"
        assert len(call_count) == 1

    def test_retry_success_on_second_attempt(self, capsys):
        """Test successful operation on second attempt after one failure"""
        call_count = []

        def operation_fails_once():
            call_count.append(1)
            if len(call_count) == 1:
                raise socket.error("Network error")
            return "success"

        result = imapbackup.retry_on_network_error(
            operation_fails_once,
            max_retries=3,
            delay=0.1
        )

        assert result == "success"
        assert len(call_count) == 2

        # Check retry message was printed
        captured = capsys.readouterr()
        assert "Retrying" in captured.out

    def test_retry_all_attempts_fail(self):
        """Test all retry attempts fail"""
        call_count = []

        def always_fails():
            call_count.append(1)
            raise socket.error("Network error")

        with pytest.raises(socket.error):
            imapbackup.retry_on_network_error(
                always_fails,
                max_retries=3,
                delay=0.1
            )

        assert len(call_count) == 3

    def test_retry_with_socket_timeout(self):
        """Test retry with socket timeout exception"""
        call_count = []

        def operation_with_timeout():
            call_count.append(1)
            if len(call_count) < 2:
                raise socket.timeout("Connection timeout")
            return "success"

        result = imapbackup.retry_on_network_error(
            operation_with_timeout,
            max_retries=3,
            delay=0.1
        )

        assert result == "success"
        assert len(call_count) == 2

    def test_retry_with_imap_error(self):
        """Test retry with IMAP4.error exception"""
        call_count = []

        def operation_with_imap_error():
            call_count.append(1)
            if len(call_count) < 2:
                raise imaplib.IMAP4.error("IMAP error")
            return "success"

        result = imapbackup.retry_on_network_error(
            operation_with_imap_error,
            max_retries=3,
            delay=0.1
        )

        assert result == "success"
        assert len(call_count) == 2

    def test_retry_non_network_error_no_retry(self):
        """Test that non-network errors are not retried"""
        call_count = []

        def operation_with_other_error():
            call_count.append(1)
            raise ValueError("Not a network error")

        with pytest.raises(ValueError):
            imapbackup.retry_on_network_error(
                operation_with_other_error,
                max_retries=3,
                delay=0.1
            )

        # Should only be called once (no retry)
        assert len(call_count) == 1

    def test_retry_exponential_backoff(self):
        """Test exponential backoff timing"""
        call_times = []

        def operation_fails_multiple_times():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise socket.error("Network error")
            return "success"

        result = imapbackup.retry_on_network_error(
            operation_fails_multiple_times,
            max_retries=3,
            delay=0.1,
            backoff=2.0
        )

        assert result == "success"
        assert len(call_times) == 3

        # Check backoff delays (approximately)
        # First retry: ~0.1s, Second retry: ~0.2s
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            # Allow some timing variance
            assert 0.08 < delay1 < 0.15  # ~0.1s
            assert 0.15 < delay2 < 0.3   # ~0.2s

    def test_retry_with_operation_name(self, capsys):
        """Test retry with operation name for logging"""
        def failing_operation():
            raise socket.error("Network error")

        with pytest.raises(socket.error):
            imapbackup.retry_on_network_error(
                failing_operation,
                max_retries=2,
                delay=0.1,
                operation_name="Test Operation"
            )

        captured = capsys.readouterr()
        assert "Test Operation" in captured.out

    def test_retry_max_retries_parameter(self):
        """Test custom max_retries parameter"""
        call_count = []

        def always_fails():
            call_count.append(1)
            raise socket.error("Network error")

        with pytest.raises(socket.error):
            imapbackup.retry_on_network_error(
                always_fails,
                max_retries=5,
                delay=0.01
            )

        assert len(call_count) == 5

    def test_retry_default_parameters(self):
        """Test with default retry parameters"""
        call_count = []

        def operation_fails_once():
            call_count.append(1)
            if len(call_count) == 1:
                raise socket.error("Network error")
            return "success"

        result = imapbackup.retry_on_network_error(operation_fails_once)

        assert result == "success"
        # Should use default max_retries (3)
        assert len(call_count) == 2


@pytest.mark.integration
class TestRetryIntegration:
    """Integration tests for retry logic with IMAP operations"""

    def test_retry_with_mock_imap_server(self, mock_imap_server):
        """Test retry logic with mock IMAP server"""
        call_count = []

        def select_with_retry():
            call_count.append(1)
            if len(call_count) < 2:
                raise socket.error("Connection reset")
            return mock_imap_server.select('"INBOX"', readonly=True)

        result = imapbackup.retry_on_network_error(select_with_retry, delay=0.1)

        assert result == ('OK', [b'100'])
        assert len(call_count) == 2
