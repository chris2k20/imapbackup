"""
Pytest configuration and shared fixtures for imapbackup tests
"""
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, MagicMock
import pytest

# Add parent directory to path so we can import imapbackup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    # Cleanup
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)


@pytest.fixture
def mock_imap_server():
    """Create a mock IMAP server for testing"""
    server = MagicMock()
    server.select.return_value = ('OK', [b'100'])  # 100 messages
    server.fetch.return_value = ('OK', [])
    server.list.return_value = ('OK', [
        b'(\\HasNoChildren) "/" "INBOX"',
        b'(\\HasNoChildren) "/" "Sent"',
        b'(\\HasNoChildren) "/" "Drafts"'
    ])
    server.logout.return_value = ('BYE', ['Logging out'])
    server.sock = MagicMock()
    return server


@pytest.fixture
def sample_messages():
    """Create sample email messages for testing"""
    messages = {}
    for i in range(1, 6):
        msg_id = f'<test{i}@example.com>'
        messages[msg_id] = i
    return messages


@pytest.fixture
def sample_mbox_content():
    """Sample mbox file content"""
    return b"""From nobody Wed Oct 10 12:00:00 2025
Message-Id: <test1@example.com>
From: sender@example.com
To: recipient@example.com
Subject: Test Message 1

This is test message 1.

From nobody Wed Oct 10 12:01:00 2025
Message-Id: <test2@example.com>
From: sender@example.com
To: recipient@example.com
Subject: Test Message 2

This is test message 2.
"""


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing"""
    return {
        'server': 'imap.example.com',
        'port': 993,
        'user': 'test@example.com',
        'pass': 'testpassword',
        'usessl': True,
        'timeout': 60,
        'basedir': '/tmp/test',
        'nospinner': True,
        'thunderbird': False,
        'icloud': False,
        'overwrite': False,
        'restore': False,
        's3_upload': False,
        'gpg_encrypt': False
    }


@pytest.fixture
def mock_s3_config():
    """Create a mock S3 configuration"""
    return {
        's3_endpoint': 'https://s3.example.com',
        's3_bucket': 'test-bucket',
        's3_access_key': 'test-access-key',
        's3_secret_key': 'test-secret-key',
        's3_prefix': 'backups/test'
    }


@pytest.fixture
def capture_output(monkeypatch):
    """Capture stdout output for testing"""
    output = []

    def mock_write(text):
        output.append(text)

    def mock_flush():
        pass

    monkeypatch.setattr('sys.stdout.write', mock_write)
    monkeypatch.setattr('sys.stdout.flush', mock_flush)

    return output


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset module state between tests"""
    yield
    # Could add cleanup code here if needed
