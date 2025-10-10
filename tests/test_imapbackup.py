"""
General unit tests for imapbackup core functions
"""
import pytest
import os
import tempfile
import hashlib
from unittest.mock import Mock, MagicMock, patch
import imapbackup


@pytest.mark.unit
class TestUtilityFunctions:
    """Tests for utility functions"""

    def test_pretty_byte_count_bytes(self):
        """Test pretty_byte_count for small values"""
        assert imapbackup.pretty_byte_count(1) == "1 byte"
        assert imapbackup.pretty_byte_count(100) == "100 bytes"
        assert imapbackup.pretty_byte_count(1023) == "1023 bytes"

    def test_pretty_byte_count_kilobytes(self):
        """Test pretty_byte_count for KB"""
        result = imapbackup.pretty_byte_count(1024)
        assert "1.00 KB" in result

        result = imapbackup.pretty_byte_count(2048)
        assert "2.00 KB" in result

    def test_pretty_byte_count_megabytes(self):
        """Test pretty_byte_count for MB"""
        result = imapbackup.pretty_byte_count(1048576)
        assert "1.000 MB" in result

        result = imapbackup.pretty_byte_count(5242880)
        assert "5.000 MB" in result

    def test_pretty_byte_count_gigabytes(self):
        """Test pretty_byte_count for GB"""
        result = imapbackup.pretty_byte_count(1073741824)
        assert "1.000 GB" in result

    def test_pretty_byte_count_terabytes(self):
        """Test pretty_byte_count for TB"""
        result = imapbackup.pretty_byte_count(1099511627776)
        assert "1.000 TB" in result

    def test_string_from_file_literal(self):
        """Test string_from_file with literal string"""
        result = imapbackup.string_from_file("test_password")
        assert result == "test_password"

    def test_string_from_file_escaped_at(self):
        """Test string_from_file with escaped @ symbol"""
        result = imapbackup.string_from_file("\\@password")
        assert result == "@password"

    def test_string_from_file_from_file(self, temp_dir):
        """Test string_from_file reading from file"""
        # Create a temporary password file
        password_file = os.path.join(temp_dir, "password.txt")
        with open(password_file, 'w') as f:
            f.write("  secret_password  \n")

        result = imapbackup.string_from_file(f"@{password_file}")
        assert result == "secret_password"

    def test_string_from_file_empty(self):
        """Test string_from_file with empty string"""
        result = imapbackup.string_from_file("")
        assert result == ""


@pytest.mark.unit
class TestMessageIDHandling:
    """Tests for Message-ID handling and regex"""

    def test_msgid_regex_simple(self):
        """Test MSGID_RE regex with simple Message-Id"""
        header = "Message-Id: <test@example.com>"
        match = imapbackup.MSGID_RE.match(header)

        assert match is not None
        assert match.group(1) == "<test@example.com>"

    def test_msgid_regex_complex(self):
        """Test MSGID_RE regex with complex Message-Id"""
        header = "Message-Id: <20251010120000.ABC123@mail.example.com>"
        match = imapbackup.MSGID_RE.match(header)

        assert match is not None
        assert "<20251010120000.ABC123@mail.example.com>" in match.group(1)

    def test_msgid_regex_case_insensitive(self):
        """Test MSGID_RE regex is case insensitive"""
        headers = [
            "Message-Id: <test@example.com>",
            "message-id: <test@example.com>",
            "MESSAGE-ID: <test@example.com>",
        ]

        for header in headers:
            match = imapbackup.MSGID_RE.match(header)
            assert match is not None

    def test_blanks_regex(self):
        """Test BLANKS_RE regex for whitespace normalization"""
        text = "Message-Id:  <test@example.com>\n  continued"
        result = imapbackup.BLANKS_RE.sub(' ', text)

        assert "  " not in result or result.count("  ") < text.count("  ")

    def test_uuid_constant(self):
        """Test UUID constant is defined"""
        assert hasattr(imapbackup, 'UUID')
        assert len(imapbackup.UUID) > 0
        assert isinstance(imapbackup.UUID, str)


@pytest.mark.unit
class TestSkipFolderException:
    """Tests for SkipFolderException"""

    def test_skip_folder_exception_creation(self):
        """Test creating SkipFolderException"""
        exc = imapbackup.SkipFolderException("Test error")
        assert str(exc) == "Test error"
        assert isinstance(exc, Exception)

    def test_skip_folder_exception_raise(self):
        """Test raising SkipFolderException"""
        with pytest.raises(imapbackup.SkipFolderException) as exc_info:
            raise imapbackup.SkipFolderException("Folder not accessible")

        assert "Folder not accessible" in str(exc_info.value)


@pytest.mark.unit
class TestParseList:
    """Tests for IMAP LIST response parsing"""

    def test_parse_paren_list_simple(self):
        """Test parsing simple parenthesized list"""
        row = r'(\HasNoChildren) "/" "INBOX"'
        result, remaining = imapbackup.parse_paren_list(row)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_parse_string_list(self):
        """Test parsing string list"""
        row = r'" / " "INBOX"'
        result = imapbackup.parse_string_list(row)

        assert isinstance(result, list)
        assert len(result) > 0


@pytest.mark.integration
class TestScanFile:
    """Tests for scan_file function"""

    def test_scan_file_not_found(self, temp_dir, capsys):
        """Test scan_file with non-existent file"""
        result = imapbackup.scan_file("nonexistent.mbox", False, True, temp_dir)

        assert result == {}
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_scan_file_overwrite_mode(self, temp_dir):
        """Test scan_file with overwrite mode returns empty dict"""
        result = imapbackup.scan_file("test.mbox", True, True, temp_dir)
        assert result == {}

    @patch('mailbox.mbox')
    def test_scan_file_with_messages(self, mock_mbox, temp_dir, sample_mbox_content):
        """Test scan_file with valid mbox file"""
        # Create a temporary mbox file
        mbox_file = os.path.join(temp_dir, "test.mbox")
        with open(mbox_file, 'wb') as f:
            f.write(sample_mbox_content)

        # Create mock message objects
        mock_msg1 = MagicMock()
        mock_msg1.get.return_value = "<test1@example.com>"

        mock_msg2 = MagicMock()
        mock_msg2.get.return_value = "<test2@example.com>"

        mock_mbox_instance = MagicMock()
        mock_mbox_instance.__iter__.return_value = [mock_msg1, mock_msg2]
        mock_mbox.return_value = mock_mbox_instance

        result = imapbackup.scan_file("test.mbox", False, True, temp_dir)

        # Should find 2 messages
        assert len(result) == 2


@pytest.mark.integration
class TestGetNames:
    """Tests for get_names function"""

    def test_get_names_basic(self, mock_imap_server):
        """Test get_names with basic folder list"""
        names = imapbackup.get_names(mock_imap_server, thunderbird=False, nospinner=True)

        assert isinstance(names, list)
        assert len(names) == 3
        # Check folder names
        folder_names = [name[0] for name in names]
        assert "INBOX" in folder_names

    def test_get_names_thunderbird_mode(self, mock_imap_server):
        """Test get_names with Thunderbird mode"""
        names = imapbackup.get_names(mock_imap_server, thunderbird=True, nospinner=True)

        assert isinstance(names, list)
        # Thunderbird uses different path structure
        for folder, filename in names:
            if folder == "INBOX":
                # Thunderbird changes to "Inbox"
                assert "Inbox" in filename or "INBOX" in filename


@pytest.mark.unit
class TestConfigParsing:
    """Tests for configuration parsing"""

    def test_parse_account_config_basic(self):
        """Test parsing basic account configuration"""
        account = {
            'name': 'test-account',
            'server': 'imap.example.com',
            'user': 'test@example.com',
            'pass': 'password123'
        }

        global_config = {
            'basedir': './backups',
            'ssl': True,
            'timeout': 60
        }

        config = imapbackup.parse_account_config(account, global_config)

        assert config['account_name'] == 'test-account'
        assert config['server'] == 'imap.example.com'
        assert config['user'] == 'test@example.com'
        assert config['usessl'] == True
        assert config['timeout'] == 60

    def test_parse_account_config_with_env_password(self, monkeypatch):
        """Test parsing account with environment variable password"""
        monkeypatch.setenv('TEST_PASSWORD', 'secret123')

        account = {
            'name': 'test-account',
            'server': 'imap.example.com',
            'user': 'test@example.com',
            'pass': 'env:TEST_PASSWORD'
        }

        global_config = {'basedir': './backups'}

        config = imapbackup.parse_account_config(account, global_config)

        assert config['pass'] == 'secret123'

    def test_parse_account_config_date_folders(self):
        """Test parsing account with date-based folders"""
        account = {
            'name': 'test-account',
            'server': 'imap.example.com',
            'user': 'test@example.com',
            'pass': 'password',
            'use_date_folders': True,
            'date_format': '%Y-%m-%d'
        }

        global_config = {'basedir': './backups'}

        config = imapbackup.parse_account_config(account, global_config)

        # Basedir should include date subfolder
        assert 'test-account' in config['basedir']
        # Should contain a date string (YYYY-MM-DD)
        import time
        expected_date = time.strftime('%Y-%m-%d')
        assert expected_date in config['basedir']


@pytest.mark.unit
class TestDirectoryCreation:
    """Tests for directory creation functions"""

    def test_create_basedir(self, temp_dir):
        """Test create_basedir function"""
        new_dir = os.path.join(temp_dir, "new_backup_dir")

        assert not os.path.exists(new_dir)

        imapbackup.create_basedir(new_dir)

        assert os.path.exists(new_dir)
        assert os.path.isdir(new_dir)

    def test_create_basedir_existing(self, temp_dir):
        """Test create_basedir with existing directory"""
        # Should not raise error
        imapbackup.create_basedir(temp_dir)
        assert os.path.exists(temp_dir)

    def test_create_folder_structure(self, temp_dir):
        """Test create_folder_structure function"""
        names = [
            ("INBOX", "INBOX.mbox"),
            ("Sent", "Sent.mbox"),
            ("Archive/2024", "Archive.2024.mbox")
        ]

        imapbackup.create_folder_structure(names, temp_dir)

        # Directory should exist
        assert os.path.exists(temp_dir)
