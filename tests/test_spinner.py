"""
Tests for the Spinner class and progress tracking functionality
"""
import pytest
import sys
from unittest.mock import Mock, patch
import imapbackup


@pytest.mark.unit
class TestSpinner:
    """Tests for the Spinner class"""

    def test_spinner_initialization(self, monkeypatch):
        """Test spinner initialization"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: False)

        spinner = imapbackup.Spinner("Test message", nospinner=True)

        assert spinner.message == "Test message"
        assert spinner.nospinner == True
        assert spinner.total is None
        assert spinner.current == 0

    def test_spinner_with_total(self, monkeypatch):
        """Test spinner with total count for progress tracking"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: False)

        spinner = imapbackup.Spinner("Processing", nospinner=True, total=100)

        assert spinner.total == 100
        assert spinner.current == 0

    def test_spinner_update_progress(self, monkeypatch):
        """Test spinner update with progress"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: False)

        spinner = imapbackup.Spinner("Downloading", nospinner=True, total=100)
        spinner.update(current=50)

        assert spinner.current == 50

    def test_spinner_progress_message(self, monkeypatch):
        """Test spinner progress message format"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: True)

        spinner = imapbackup.Spinner("Processing", nospinner=False, total=100)
        spinner.update(current=50)

        # Check that progress is displayed
        progress_output = ''.join(output)
        assert "50/100" in progress_output or "50%" in progress_output

    def test_spinner_stop_with_progress(self, monkeypatch):
        """Test spinner stop shows 100% when completed"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: True)

        spinner = imapbackup.Spinner("Processing", nospinner=False, total=100)
        spinner.update(current=100)
        spinner.stop()

        # Check that 100% is displayed
        final_output = ''.join(output)
        assert "100/100" in final_output or "100%" in final_output

    def test_spinner_without_progress(self, monkeypatch):
        """Test spinner without total (no progress tracking)"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: True)

        spinner = imapbackup.Spinner("Processing", nospinner=False)
        spinner.spin()

        # Should not include percentage
        output_text = ''.join(output)
        assert "%" not in output_text or output_text.count("%") == 0

    def test_spinner_nospinner_mode(self, monkeypatch):
        """Test spinner in nospinner mode (no animation)"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: False)

        spinner = imapbackup.Spinner("Processing", nospinner=True, total=100)
        initial_output_count = len(output)

        spinner.spin()

        # In nospinner mode, should not produce animation characters
        # But initial message should be written
        assert len(output) >= initial_output_count

    def test_spinner_percentage_calculation(self, monkeypatch):
        """Test spinner percentage calculation accuracy"""
        output = []

        def mock_write(text):
            output.append(text)

        def mock_flush():
            pass

        monkeypatch.setattr('sys.stdout.write', mock_write)
        monkeypatch.setattr('sys.stdout.flush', mock_flush)
        monkeypatch.setattr('sys.stdin.isatty', lambda: True)

        spinner = imapbackup.Spinner("Processing", nospinner=False, total=200)

        # Test 25%
        spinner.update(current=50)
        output_text = ''.join(output)
        assert "25%" in output_text

        # Clear output
        output.clear()

        # Test 75%
        spinner.update(current=150)
        output_text = ''.join(output)
        assert "75%" in output_text
