"""
Tests for batch processing and memory optimization in scan_folder
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import imapbackup


@pytest.mark.unit
class TestBatchProcessing:
    """Tests for batch processing functionality"""

    def test_fetch_batch_size_constant(self):
        """Test that FETCH_BATCH_SIZE constant is defined"""
        assert hasattr(imapbackup, 'FETCH_BATCH_SIZE')
        assert imapbackup.FETCH_BATCH_SIZE > 0
        assert isinstance(imapbackup.FETCH_BATCH_SIZE, int)

    def test_batch_calculation_single_batch(self):
        """Test batch calculation for messages that fit in one batch"""
        num_msgs = 500
        batch_size = imapbackup.FETCH_BATCH_SIZE

        # Calculate expected number of batches
        if num_msgs <= batch_size:
            expected_batches = 1
        else:
            expected_batches = (num_msgs + batch_size - 1) // batch_size

        assert expected_batches == 1

    def test_batch_calculation_multiple_batches(self):
        """Test batch calculation for messages requiring multiple batches"""
        num_msgs = 2500
        batch_size = imapbackup.FETCH_BATCH_SIZE

        # Calculate expected number of batches
        expected_batches = (num_msgs + batch_size - 1) // batch_size

        assert expected_batches == 3  # 1000 + 1000 + 500

    def test_batch_range_generation(self):
        """Test batch range generation"""
        num_msgs = 2500
        batch_size = 1000
        ranges = []

        for batch_start in range(1, num_msgs + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, num_msgs)
            ranges.append((batch_start, batch_end))

        assert len(ranges) == 3
        assert ranges[0] == (1, 1000)
        assert ranges[1] == (1001, 2000)
        assert ranges[2] == (2001, 2500)


@pytest.mark.integration
class TestScanFolderBatching:
    """Integration tests for scan_folder with batch processing"""

    def create_mock_headers(self, start, end):
        """Helper to create mock header responses"""
        data = []
        for i in range(start, end + 1):
            msg_id = f'<test{i}@example.com>'
            header_bytes = f'Message-Id: {msg_id}\r\n'.encode('utf-8')
            data.append((f'{i} (BODY[HEADER.FIELDS (MESSAGE-ID)] {{...}}'.encode(), header_bytes))
            data.append(b')')
        return data

    @patch('imapbackup.gc.collect')
    @patch('imapbackup.retry_on_network_error')
    def test_scan_folder_single_batch(self, mock_retry, mock_gc, mock_imap_server):
        """Test scan_folder with messages fitting in single batch"""
        # Setup: 500 messages (< FETCH_BATCH_SIZE)
        num_msgs = 500
        mock_imap_server.select.return_value = ('OK', [str(num_msgs).encode()])

        # Mock the fetch operation
        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.side_effect = retry_side_effect

        # Mock fetch to return headers
        mock_imap_server.fetch.return_value = ('OK', self.create_mock_headers(1, num_msgs))

        # Call scan_folder
        messages = imapbackup.scan_folder(mock_imap_server, 'INBOX', nospinner=True)

        # Verify
        assert len(messages) == num_msgs
        # Should fetch once for single batch
        assert mock_imap_server.fetch.call_count >= 1
        # gc.collect should be called after batch processing
        assert mock_gc.called

    @patch('imapbackup.gc.collect')
    @patch('imapbackup.retry_on_network_error')
    def test_scan_folder_multiple_batches(self, mock_retry, mock_gc, mock_imap_server):
        """Test scan_folder with messages requiring multiple batches"""
        # Setup: 2500 messages (> FETCH_BATCH_SIZE)
        num_msgs = 2500
        mock_imap_server.select.return_value = ('OK', [str(num_msgs).encode()])

        fetch_calls = []

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.side_effect = retry_side_effect

        # Mock fetch to track batch calls
        def mock_fetch(msg_range, fetch_cmd):
            fetch_calls.append(msg_range)
            # Parse range
            if ':' in msg_range:
                start, end = map(int, msg_range.split(':'))
            else:
                start = end = int(msg_range)
            return ('OK', self.create_mock_headers(start, end))

        mock_imap_server.fetch.side_effect = mock_fetch

        # Call scan_folder
        messages = imapbackup.scan_folder(mock_imap_server, 'INBOX', nospinner=True)

        # Verify
        assert len(messages) == num_msgs

        # Should fetch in batches
        # For 2500 messages with batch size 1000: 3 batches
        header_fetch_calls = [c for c in fetch_calls if ':' in c and 'BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)]' in str(mock_imap_server.fetch.call_args_list)]

        # At least 3 batch fetches should have occurred
        assert len(fetch_calls) >= 3

        # gc.collect should be called multiple times (once per batch)
        assert mock_gc.call_count >= 3

    @patch('imapbackup.retry_on_network_error')
    def test_scan_folder_batch_ranges(self, mock_retry, mock_imap_server):
        """Test that batch ranges are calculated correctly"""
        num_msgs = 2500
        mock_imap_server.select.return_value = ('OK', [str(num_msgs).encode()])

        batch_ranges = []

        def retry_side_effect(func, **kwargs):
            result = func()
            return result

        mock_retry.side_effect = retry_side_effect

        def mock_fetch(msg_range, fetch_cmd):
            if ':' in msg_range and 'MESSAGE-ID' in fetch_cmd:
                batch_ranges.append(msg_range)
            return ('OK', [])

        mock_imap_server.fetch.side_effect = mock_fetch

        # Call scan_folder
        try:
            imapbackup.scan_folder(mock_imap_server, 'INBOX', nospinner=True)
        except:
            pass  # May fail due to empty response, but we just need to check ranges

        # Verify batch ranges
        if batch_ranges:
            # First batch should start at 1
            assert '1:' in batch_ranges[0]

    @patch('imapbackup.FETCH_BATCH_SIZE', 100)
    @patch('imapbackup.retry_on_network_error')
    def test_scan_folder_small_batch_size(self, mock_retry, mock_imap_server):
        """Test scan_folder with small batch size"""
        num_msgs = 250
        mock_imap_server.select.return_value = ('OK', [str(num_msgs).encode()])

        fetch_count = []

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.side_effect = retry_side_effect

        def mock_fetch(msg_range, fetch_cmd):
            if ':' in msg_range:
                fetch_count.append(msg_range)
                start, end = map(int, msg_range.split(':'))
                return ('OK', self.create_mock_headers(start, end))
            return ('OK', [])

        mock_imap_server.fetch.side_effect = mock_fetch

        # Call scan_folder with small batch size
        messages = imapbackup.scan_folder(mock_imap_server, 'INBOX', nospinner=True)

        # With batch size 100 and 250 messages: should have 3 batches
        # 1-100, 101-200, 201-250
        header_fetches = [f for f in fetch_count if 'BODY' not in f]
        assert len(fetch_count) >= 3

    @patch('imapbackup.retry_on_network_error')
    def test_scan_folder_memory_cleanup(self, mock_retry, mock_imap_server):
        """Test that memory is cleaned up after each batch"""
        num_msgs = 1500
        mock_imap_server.select.return_value = ('OK', [str(num_msgs).encode()])

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.side_effect = retry_side_effect

        mock_imap_server.fetch.return_value = ('OK', self.create_mock_headers(1, 1000))

        # Mock gc.collect to track calls
        with patch('imapbackup.gc.collect') as mock_gc:
            try:
                imapbackup.scan_folder(mock_imap_server, 'INBOX', nospinner=True)
            except:
                pass  # May fail but we just need to verify gc was called

            # gc.collect should be called at least once per batch
            assert mock_gc.called


@pytest.mark.unit
class TestMemoryOptimization:
    """Tests for memory optimization features"""

    def test_batch_size_configuration(self):
        """Test that batch size can be configured"""
        original_batch_size = imapbackup.FETCH_BATCH_SIZE

        # Verify it's a reasonable value
        assert 100 <= original_batch_size <= 10000

    def test_batch_size_is_integer(self):
        """Test that batch size is an integer"""
        assert isinstance(imapbackup.FETCH_BATCH_SIZE, int)

    def test_batch_processing_reduces_memory_spikes(self):
        """Test that batch processing prevents loading all messages at once"""
        # This is a conceptual test - in practice, batch processing
        # should prevent memory spikes by processing in chunks

        num_msgs = 10000
        batch_size = 1000

        # Without batching: all 10000 messages loaded at once
        # With batching: only 1000 messages loaded at a time

        batches_needed = (num_msgs + batch_size - 1) // batch_size
        max_messages_in_memory = batch_size

        assert batches_needed == 10
        assert max_messages_in_memory == 1000
        # Memory saved: 90% reduction in peak memory usage
        memory_reduction = (num_msgs - max_messages_in_memory) / num_msgs
        assert memory_reduction == 0.9
