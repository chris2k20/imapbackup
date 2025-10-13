"""
Security tests for GPG functionality - ensures encryption failures are handled properly
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import imapbackup


@pytest.mark.unit
class TestGPGSecurity:
    """Security tests for GPG encryption"""

    def test_gpg_import_returns_none_on_failure(self):
        """Test that import_gpg_key returns None when it fails"""
        # Test with invalid URL
        result = imapbackup.import_gpg_key("https://invalid-url-that-does-not-exist.example.com/key.asc")
        assert result is None

    def test_gpg_import_returns_none_on_invalid_key(self):
        """Test that import_gpg_key returns None for invalid key content"""
        result = imapbackup.import_gpg_key("not a valid key")
        assert result is None

    @patch('imapbackup.import_gpg_key')
    @patch('imapbackup.connect_and_login')
    @patch('imapbackup.get_names')
    @patch('imapbackup.create_basedir')
    @patch('imapbackup.create_folder_structure')
    def test_process_account_fails_when_gpg_key_import_fails(
        self, mock_create_folder, mock_create_basedir, mock_get_names,
        mock_connect, mock_import_key
    ):
        """Test that process_account returns False when GPG key import fails"""
        # Setup mocks
        mock_server = MagicMock()
        mock_connect.return_value = mock_server
        mock_get_names.return_value = []
        mock_import_key.return_value = None  # Simulate key import failure

        # Create config with GPG encryption enabled
        config = {
            'server': 'imap.example.com',
            'port': 993,
            'user': 'test@example.com',
            'pass': 'password',
            'account_name': 'test-account',
            'basedir': '/tmp/test',
            'gpg_encrypt': True,
            'gpg_import_key': 'https://example.com/key.asc',
            'gpg_recipient': 'test@example.com'
        }

        # Call process_account
        result = imapbackup.process_account(config)

        # Verify it returns False (failure)
        assert result == False

        # Verify server.logout() was called
        mock_server.logout.assert_called_once()

    @patch('imapbackup.import_gpg_key')
    @patch('imapbackup.connect_and_login')
    @patch('imapbackup.get_names')
    @patch('imapbackup.create_basedir')
    @patch('imapbackup.create_folder_structure')
    def test_process_account_continues_when_gpg_key_import_succeeds(
        self, mock_create_folder, mock_create_basedir, mock_get_names,
        mock_connect, mock_import_key
    ):
        """Test that process_account continues when GPG key import succeeds"""
        # Setup mocks
        mock_server = MagicMock()
        mock_connect.return_value = mock_server
        mock_get_names.return_value = []  # No folders to process
        mock_import_key.return_value = 'ABCD1234EFGH5678IJKL9012MNOP3456QRST7890'  # Return fingerprint

        # Create config with GPG encryption enabled
        config = {
            'server': 'imap.example.com',
            'port': 993,
            'user': 'test@example.com',
            'pass': 'password',
            'account_name': 'test-account',
            'basedir': '/tmp/test',
            'gpg_encrypt': True,
            'gpg_import_key': 'https://example.com/key.asc',
            'gpg_recipient': 'test@example.com'
        }

        # Call process_account
        result = imapbackup.process_account(config)

        # Verify it returns True (success) - even with no folders
        assert result == True

        # Verify server.logout() was called at the end
        mock_server.logout.assert_called()

    @patch('imapbackup.import_gpg_key')
    @patch('imapbackup.connect_and_login')
    @patch('imapbackup.get_names')
    @patch('imapbackup.create_basedir')
    @patch('imapbackup.create_folder_structure')
    def test_process_account_skips_gpg_import_when_not_configured(
        self, mock_create_folder, mock_create_basedir, mock_get_names,
        mock_connect, mock_import_key
    ):
        """Test that GPG import is skipped when not configured"""
        # Setup mocks
        mock_server = MagicMock()
        mock_connect.return_value = mock_server
        mock_get_names.return_value = []

        # Create config WITHOUT GPG encryption
        config = {
            'server': 'imap.example.com',
            'port': 993,
            'user': 'test@example.com',
            'pass': 'password',
            'account_name': 'test-account',
            'basedir': '/tmp/test',
            'gpg_encrypt': False  # GPG disabled
        }

        # Call process_account
        result = imapbackup.process_account(config)

        # Verify import_gpg_key was NOT called
        mock_import_key.assert_not_called()

        # Verify it returns True (success)
        assert result == True


@pytest.mark.integration
class TestGPGSecurityIntegration:
    """Integration tests for GPG security"""

    @patch('subprocess.run')
    def test_gpg_import_with_network_failure(self, mock_subprocess):
        """Test GPG import handles network failures properly"""
        # Simulate network failure
        mock_subprocess.side_effect = Exception("Network error")

        result = imapbackup.import_gpg_key("https://keys.example.com/public.asc")

        assert result is None

    @patch('subprocess.run')
    def test_gpg_not_installed(self, mock_subprocess):
        """Test GPG import handles missing GPG binary"""
        # Simulate GPG not installed
        mock_subprocess.side_effect = FileNotFoundError("gpg not found")

        result = imapbackup.import_gpg_key("https://keys.example.com/public.asc")

        assert result is None

    def test_security_message_printed_on_failure(self, capsys):
        """Test that security warnings are printed when GPG import fails"""
        # Call import_gpg_key with invalid input
        imapbackup.import_gpg_key("invalid-key-source")

        # Capture output
        captured = capsys.readouterr()

        # Verify warning message was printed
        assert "WARNING" in captured.out or "Failed to import GPG key" in captured.out


@pytest.mark.unit
class TestEncryptionFailsafe:
    """Tests to ensure encryption doesn't silently fail"""

    def test_encrypt_file_requires_valid_recipient(self, temp_dir):
        """Test that encryption fails with invalid recipient"""
        import os
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test data")

        with pytest.raises(Exception):
            imapbackup.encrypt_file_gpg(test_file, "invalid-recipient-xyz-123")

    def test_encrypt_file_requires_valid_input_file(self):
        """Test that encryption fails with non-existent file"""
        with pytest.raises(Exception):
            imapbackup.encrypt_file_gpg("/tmp/nonexistent-file-xyz-123.txt", "test@example.com")


@pytest.mark.unit
class TestS3EncryptionFailures:
    """Tests for S3 upload phase encryption failures"""

    @patch('os.path.exists')
    @patch('imapbackup.encrypt_file_gpg')
    @patch('imapbackup.connect_and_login')
    @patch('imapbackup.get_names')
    @patch('imapbackup.create_basedir')
    @patch('imapbackup.create_folder_structure')
    def test_process_account_fails_on_s3_encryption_failure(
        self, mock_create_folder, mock_create_basedir, mock_get_names,
        mock_connect, mock_encrypt, mock_exists
    ):
        """Test that process_account returns False when S3 encryption fails"""
        # Setup mocks
        mock_server = MagicMock()
        mock_connect.return_value = mock_server
        mock_get_names.return_value = [('INBOX', 'INBOX.mbox')]
        mock_exists.return_value = True

        # Simulate encryption failure
        mock_encrypt.side_effect = Exception("GPG encryption failed: invalid recipient")

        # Create config with S3 upload and GPG encryption enabled
        config = {
            'server': 'imap.example.com',
            'port': 993,
            'user': 'test@example.com',
            'pass': 'password',
            'account_name': 'test-account',
            'basedir': '/tmp/test',
            's3_upload': True,
            's3_endpoint': 'https://s3.example.com',
            's3_bucket': 'test-bucket',
            's3_access_key': 'test-key',
            's3_secret_key': 'test-secret',
            'gpg_encrypt': True,
            'gpg_recipient': 'invalid@example.com'
        }

        # Call process_account
        result = imapbackup.process_account(config)

        # Verify it returns False (failure)
        assert result == False

        # Verify server.logout() was called
        mock_server.logout.assert_called()

    @patch('os.path.exists')
    @patch('os.remove')
    @patch('imapbackup.encrypt_file_gpg')
    @patch('imapbackup.upload_to_s3')
    @patch('imapbackup.connect_and_login')
    @patch('imapbackup.get_names')
    @patch('imapbackup.create_basedir')
    @patch('imapbackup.create_folder_structure')
    def test_no_files_uploaded_when_encryption_fails(
        self, mock_create_folder, mock_create_basedir, mock_get_names,
        mock_connect, mock_upload, mock_encrypt, mock_remove, mock_exists
    ):
        """Test that no files are uploaded to S3 when encryption fails"""
        # Setup mocks
        mock_server = MagicMock()
        mock_connect.return_value = mock_server
        mock_get_names.return_value = [('INBOX', 'INBOX.mbox'), ('Sent', 'Sent.mbox')]
        mock_exists.return_value = True

        # Simulate encryption failure for all files
        mock_encrypt.side_effect = Exception("GPG encryption failed")

        # Create config with S3 upload and GPG encryption enabled
        config = {
            'server': 'imap.example.com',
            'port': 993,
            'user': 'test@example.com',
            'pass': 'password',
            'account_name': 'test-account',
            'basedir': '/tmp/test',
            's3_upload': True,
            's3_endpoint': 'https://s3.example.com',
            's3_bucket': 'test-bucket',
            's3_access_key': 'test-key',
            's3_secret_key': 'test-secret',
            'gpg_encrypt': True,
            'gpg_recipient': 'test@example.com'
        }

        # Call process_account
        result = imapbackup.process_account(config)

        # Verify it returns False (failure)
        assert result == False

        # Verify upload_to_s3 was NOT called (no files should be uploaded)
        mock_upload.assert_not_called()

    @patch('os.path.exists')
    @patch('imapbackup.encrypt_file_gpg')
    @patch('imapbackup.connect_and_login')
    @patch('imapbackup.get_names')
    @patch('imapbackup.create_basedir')
    @patch('imapbackup.create_folder_structure')
    def test_error_messages_printed_on_encryption_failure(
        self, mock_create_folder, mock_create_basedir, mock_get_names,
        mock_connect, mock_encrypt, mock_exists, capsys
    ):
        """Test that proper error messages are printed when encryption fails"""
        # Setup mocks
        mock_server = MagicMock()
        mock_connect.return_value = mock_server
        mock_get_names.return_value = [('INBOX', 'INBOX.mbox')]
        mock_exists.return_value = True

        # Simulate encryption failure
        mock_encrypt.side_effect = Exception("GPG encryption failed: key not found")

        # Create config with S3 upload and GPG encryption enabled
        config = {
            'server': 'imap.example.com',
            'port': 993,
            'user': 'test@example.com',
            'pass': 'password',
            'account_name': 'test-account',
            'basedir': '/tmp/test',
            's3_upload': True,
            's3_endpoint': 'https://s3.example.com',
            's3_bucket': 'test-bucket',
            's3_access_key': 'test-key',
            's3_secret_key': 'test-secret',
            'gpg_encrypt': True,
            'gpg_recipient': 'test@example.com'
        }

        # Call process_account
        result = imapbackup.process_account(config)

        # Capture output
        captured = capsys.readouterr()

        # Verify it returns False
        assert result == False

        # Verify error messages were printed
        assert "ERROR: GPG encryption failed for one or more files" in captured.out
        assert "ERROR: Cannot upload to S3 with encryption failures" in captured.out
        assert "ERROR: Aborting to prevent unencrypted data exposure" in captured.out

    @patch('os.path.exists')
    @patch('os.remove')
    @patch('imapbackup.encrypt_file_gpg')
    @patch('imapbackup.upload_to_s3')
    @patch('imapbackup.connect_and_login')
    @patch('imapbackup.get_names')
    @patch('imapbackup.create_basedir')
    @patch('imapbackup.create_folder_structure')
    def test_partial_encryption_failure_still_fails(
        self, mock_create_folder, mock_create_basedir, mock_get_names,
        mock_connect, mock_upload, mock_encrypt, mock_remove, mock_exists
    ):
        """Test that even partial encryption failures cause the backup to fail"""
        # Setup mocks
        mock_server = MagicMock()
        mock_connect.return_value = mock_server
        mock_get_names.return_value = [
            ('INBOX', 'INBOX.mbox'),
            ('Sent', 'Sent.mbox'),
            ('Drafts', 'Drafts.mbox')
        ]
        mock_exists.return_value = True

        # Simulate encryption success for first file, failure for second
        mock_encrypt.side_effect = [
            '/tmp/test/INBOX.mbox.gpg',  # Success for first file
            Exception("GPG encryption failed"),  # Failure for second file
        ]

        # Create config with S3 upload and GPG encryption enabled
        config = {
            'server': 'imap.example.com',
            'port': 993,
            'user': 'test@example.com',
            'pass': 'password',
            'account_name': 'test-account',
            'basedir': '/tmp/test',
            's3_upload': True,
            's3_endpoint': 'https://s3.example.com',
            's3_bucket': 'test-bucket',
            's3_access_key': 'test-key',
            's3_secret_key': 'test-secret',
            'gpg_encrypt': True,
            'gpg_recipient': 'test@example.com'
        }

        # Call process_account
        result = imapbackup.process_account(config)

        # Verify it returns False (failure even with partial success)
        assert result == False

        # Verify upload_to_s3 was NOT called
        mock_upload.assert_not_called()
