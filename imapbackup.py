#!/usr/bin/env python3 -u

"""IMAP Incremental Backup Script"""
__version__ = "1.4h"
__author__ = "Rui Carmo (http://taoofmac.com)"
__copyright__ = "(C) 2006-2018 Rui Carmo. Code under MIT License.(C)"
__contributors__ = "jwagnerhki, Bob Ippolito, Michael Leonhard, Giuseppe Scrivano <gscrivano@gnu.org>, Ronan Sheth, Brandon Long, Christian Schanz, A. Bovett, Mark Feit, Marco Machicao"

# = Contributors =
# https://github.com/mmachicao: Port impapbackup core use case to python3.8. Mailbox does not support compression.
# http://github.com/markfeit: Allow password to be read from a file
# http://github.com/jwagnerhki: fix for message_id checks
# A. Bovett: Modifications for Thunderbird compatibility and disabling spinner in Windows
#  Christian Schanz: added target directory parameter
# Brandon Long (Gmail team): Reminder to use BODY.PEEK instead of BODY
# Ronan Sheth: hashlib patch (this now requires Python 2.5, although reverting it back is trivial)
# Giuseppe Scrivano: Added support for folders.
# Michael Leonhard: LIST result parsing, SSL support, revamped argument processing,
#                   moved spinner into class, extended recv fix to Windows
# Bob Ippolito: fix for MemoryError on socket recv, http://python.org/sf/1092502
# Rui Carmo: original author, up to v1.2e

# = TODO =
# - Migrate mailbox usage from rfc822 module to email module
# - Investigate using the noseek mailbox/email option to improve speed
# - Use the email module to normalize downloaded messages
#   and add missing Message-Id
# - Test parseList() and its descendents on other imapds
# - Add option to download only subscribed folders
# - Add regex option to filter folders
# - Use a single IMAP command to get Message-IDs
# - Use a single IMAP command to fetch the messages
# - Patch Python's ssl module to do proper checking of certificate chain
# - Patch Python's ssl module to raise good exceptions
# - Submit patch of socket._fileobject.read
# - Improve imaplib module with LIST parsing code, submit patch
# DONE:
# v1.4h
# - Add timeout option
# v1.3c
# - Add SSL support
# - Support host:port
# - Cleaned up code using PyLint to identify problems
#   pylint -f html --indent-string="  " --max-line-length=90 imapbackup.py > report.html
import getpass
import os
import gc
import sys
import time
import getopt
import mailbox
import imaplib
import socket
import re
import hashlib
import subprocess
import tempfile

# Try to import YAML, but make it optional
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

class SkipFolderException(Exception):
    """Indicates aborting processing of current folder, continue with next folder."""
    pass


class Spinner:
    """Prints out message with cute spinner, indicating progress"""

    def __init__(self, message, nospinner, total=None):
        """Spinner constructor

        Args:
            message: Base message to display
            nospinner: If True, disable spinner animation
            total: Optional total count for progress tracking
        """
        self.glyphs = "|/-\\"
        self.pos = 0
        self.message = message
        self.nospinner = nospinner
        self.total = total
        self.current = 0
        sys.stdout.write(message)
        sys.stdout.flush()
        self.spin()

    def update(self, current=None, message=None):
        """Update progress

        Args:
            current: Current progress count
            message: Optional message override
        """
        if current is not None:
            self.current = current
        if message is not None:
            self.message = message
        self.spin()

    def spin(self):
        """Rotate the spinner"""
        if sys.stdin.isatty() and not self.nospinner:
            display_msg = self.message

            # Add progress if total is set
            if self.total is not None and self.total > 0:
                percentage = int((self.current / self.total) * 100)
                display_msg = "%s (%d/%d, %d%%)" % (self.message, self.current, self.total, percentage)

            sys.stdout.write("\r" + display_msg + " " + self.glyphs[self.pos])
            sys.stdout.flush()
            self.pos = (self.pos+1) % len(self.glyphs)

    def stop(self):
        """Erase the spinner from the screen"""
        if sys.stdin.isatty() and not self.nospinner:
            display_msg = self.message

            # Add final progress if total is set
            if self.total is not None and self.total > 0:
                display_msg = "%s (%d/%d, 100%%)" % (self.message, self.total, self.total)

            sys.stdout.write("\r" + display_msg + "  ")
            sys.stdout.write("\r" + display_msg)
            sys.stdout.flush()


def pretty_byte_count(num):
    """Converts integer into a human friendly count of bytes, eg: 12.243 MB"""
    if num == 1:
        return "1 byte"
    elif num < 1024:
        return "%s bytes" % num
    elif num < 1048576:
        return "%.2f KB" % (num/1024.0)
    elif num < 1073741824:
        return "%.3f MB" % (num/1048576.0)
    elif num < 1099511627776:
        return "%.3f GB" % (num/1073741824.0)
    else:
        return "%.3f TB" % (num/1099511627776.0)


# Regular expressions for parsing
MSGID_RE = re.compile(r"^Message-Id: (.+)", re.IGNORECASE + re.MULTILINE)
BLANKS_RE = re.compile(r'\s+', re.MULTILINE)

# Constants
UUID = '19AF1258-1AAF-44EF-9D9A-731079D6FAD7'  # Used to generate Message-Ids

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # exponential backoff multiplier

# Memory optimization configuration
FETCH_BATCH_SIZE = 1000  # Number of messages to fetch headers for in one batch


def retry_on_network_error(func, max_retries=DEFAULT_MAX_RETRIES, delay=DEFAULT_RETRY_DELAY, backoff=DEFAULT_RETRY_BACKOFF, operation_name=None):
    """
    Retry a function that may fail due to network errors.

    Args:
        func: Callable function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Exponential backoff multiplier
        operation_name: Optional name for logging purposes

    Returns:
        The return value of the function if successful

    Raises:
        The last exception encountered if all retries fail
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_retries):
        try:
            return func()
        except (socket.error, socket.timeout, imaplib.IMAP4.error) as e:
            last_exception = e
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                retry_msg = "Attempt %d/%d failed" % (attempt + 1, max_retries)
                if operation_name:
                    retry_msg = "%s: %s" % (operation_name, retry_msg)
                retry_msg += ". Retrying in %.1f seconds..." % current_delay
                print ("\n  %s" % retry_msg)
                time.sleep(current_delay)
                current_delay *= backoff
            else:
                error_msg = "All %d attempts failed" % max_retries
                if operation_name:
                    error_msg = "%s: %s" % (operation_name, error_msg)
                print ("\n  %s" % error_msg)
        except Exception as e:
            # For non-network errors, don't retry
            raise

    # All retries exhausted
    raise last_exception


def string_from_file(value):
    """
    Read a string from a file or return the string unchanged.

    If the string begins with '@', the remainder of the string
    will be treated as a path to the file to be read.  Precede
    the '@' with a '\' to treat it as a literal.
    """
    assert isinstance(value, str)

    if not value or value[0] not in ["\\", "@"]:
        return value

    if value[0] == "\\":
        return value[1:]

    with open(os.path.expanduser(value[1:]), 'r') as content:
        return content.read().strip()


def import_gpg_key(source):
    """
    Import a GPG public key from various sources.

    Supports:
    - Environment variable: GPG_PUBLIC_KEY
    - File path: /path/to/key.asc or ~/keys/public.asc
    - URL: https://example.com/public-key.asc
    - Raw key content as string

    Args:
        source: String containing env var name, file path, URL, or key content

    Returns:
        Fingerprint string if import succeeded, None otherwise
    """
    try:
        key_content = None
        source_description = ""

        # Check if GPG is available
        try:
            subprocess.run(['gpg', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("GPG not found. Please install GPG (gnupg) to use key import.")

        # 1. Check environment variable
        if source.startswith('env:') or source.startswith('ENV:'):
            env_var = source[4:]
            key_content = os.environ.get(env_var)
            if not key_content:
                raise Exception("Environment variable '%s' not found or empty" % env_var)
            source_description = "environment variable %s" % env_var

        # 2. Check if it's a URL (http:// or https://)
        elif source.startswith('http://') or source.startswith('https://'):
            # Retry logic for downloading GPG key
            def download_key_operation():
                try:
                    # Try curl first
                    try:
                        result = subprocess.run(
                            ['curl', '-fsSL', source],
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=30
                        )
                        return result.stdout
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        # Fall back to wget
                        result = subprocess.run(
                            ['wget', '-qO-', source],
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=30
                        )
                        return result.stdout
                except subprocess.TimeoutExpired:
                    raise socket.timeout("Timeout while downloading key")
                except subprocess.CalledProcessError as e:
                    raise socket.error("Failed to download key: %s" % e.stderr)

            try:
                key_content = retry_on_network_error(
                    download_key_operation,
                    max_retries=3,
                    operation_name="Download GPG key from %s" % source
                )

                if not key_content or len(key_content) < 100:
                    raise Exception("Downloaded key appears to be empty or invalid")
                source_description = "URL %s" % source
            except Exception as e:
                raise Exception("Failed to download key from URL after retries: %s" % str(e))

        # 3. Check if it's a file path
        elif os.path.exists(os.path.expanduser(source)):
            file_path = os.path.expanduser(source)
            with open(file_path, 'r') as f:
                key_content = f.read()
            source_description = "file %s" % file_path

        # 4. Assume it's raw key content
        else:
            # Check if it looks like a GPG key
            if '-----BEGIN PGP PUBLIC KEY BLOCK-----' in source:
                key_content = source
                source_description = "provided key content"
            else:
                raise Exception("Invalid key source: not a valid file, URL, environment variable, or key content")

        # Validate key content
        if not key_content:
            raise Exception("No key content found")

        if '-----BEGIN PGP PUBLIC KEY BLOCK-----' not in key_content:
            raise Exception("Invalid GPG key format (missing PGP PUBLIC KEY BLOCK header)")

        # Import the key using GPG
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.asc') as f:
            f.write(key_content)
            temp_key_file = f.name

        try:
            # First, extract fingerprint using show-only
            fingerprint = None
            try:
                show_cmd = ['gpg', '--batch', '--import-options', 'show-only', '--import', '--with-colons', temp_key_file]
                show_result = subprocess.run(show_cmd, capture_output=True, text=True, check=True)
                for line in show_result.stdout.split('\n'):
                    if line.startswith('fpr:'):
                        fields = line.split(':')
                        if len(fields) >= 10 and len(fields[9]) == 40:
                            fingerprint = fields[9]
                            print("  Extracted fingerprint: %s" % fingerprint)
                            break
            except:
                pass  # Will try after import

            # Import the key
            cmd = ['gpg', '--batch', '--import', temp_key_file]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Check if key was skipped due to missing user ID
            if 'contains no user ID' in result.stderr or 'w/o user IDs' in result.stderr:
                print("\nERROR: GPG key import failed - key has no user ID")
                print("ERROR: The key from '%s' does not contain a user ID." % source_description)
                print("ERROR: This typically happens with keys from keys.openpgp.org when the email isn't verified.")
                print("ERROR:")
                print("ERROR: Solutions:")
                print("ERROR: 1. Verify your email on keys.openpgp.org and use the by-email URL")
                print("ERROR: 2. Provide the full PGP public key block directly (with user ID)")
                print("ERROR: 3. Upload your key to keyserver.ubuntu.com with full user ID")
                return None

            print("  Successfully imported GPG key from %s" % source_description)

            # If fingerprint extraction failed before import, try after
            if not fingerprint:
                try:
                    list_cmd = ['gpg', '--batch', '--list-keys', '--with-colons']
                    list_result = subprocess.run(list_cmd, capture_output=True, text=True, check=True)
                    for line in list_result.stdout.split('\n'):
                        if line.startswith('fpr:'):
                            fields = line.split(':')
                            if len(fields) >= 10 and len(fields[9]) == 40:
                                fingerprint = fields[9]
                                break
                except:
                    pass

            # Return fingerprint if found, otherwise True for backwards compatibility
            return fingerprint if fingerprint else True

        finally:
            # Clean up temp file
            if os.path.exists(temp_key_file):
                os.unlink(temp_key_file)

    except Exception as e:
        print("  WARNING: Failed to import GPG key: %s" % str(e))
        return None


def encrypt_file_gpg(input_file, recipient):
    """Encrypt a file using GPG and return the path to encrypted file"""
    output_file = input_file + '.gpg'

    try:
        # Run GPG encryption
        cmd = [
            'gpg',
            '--batch',
            '--yes',
            '--trust-model', 'always',
            '--no-auto-key-retrieve',  # Prevent GPG from trying to fetch keys during encryption
            '--encrypt',
            '--recipient', recipient,
            '--output', output_file,
            input_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if os.path.exists(output_file):
            print ("  Encrypted with GPG for recipient: %s" % recipient)
            return output_file
        else:
            raise Exception("GPG encryption failed: output file not created")

    except subprocess.CalledProcessError as e:
        raise Exception("GPG encryption failed: %s\n%s" % (e.stderr, e.stdout))
    except FileNotFoundError:
        raise Exception("GPG not found. Please install GPG (gnupg) to use encryption.")


def decrypt_file_gpg(input_file):
    """Decrypt a GPG-encrypted file and return the path to decrypted file"""
    # Remove .gpg extension for output file
    if input_file.endswith('.gpg'):
        output_file = input_file[:-4]
    else:
        output_file = input_file + '.decrypted'

    try:
        # Run GPG decryption
        cmd = [
            'gpg',
            '--batch',
            '--yes',
            '--decrypt',
            '--output', output_file,
            input_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if os.path.exists(output_file):
            print ("  Decrypted: %s" % os.path.basename(input_file))
            return output_file
        else:
            raise Exception("GPG decryption failed: output file not created")

    except subprocess.CalledProcessError as e:
        raise Exception("GPG decryption failed: %s\n%s" % (e.stderr, e.stdout))
    except FileNotFoundError:
        raise Exception("GPG not found. Please install GPG (gnupg) to use decryption.")


def download_from_s3(filename, config, destination_dir):
    """Download a file from S3-compatible storage using AWS CLI with retry logic"""
    # Check if aws CLI is available
    try:
        subprocess.run(['aws', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise Exception("AWS CLI not found. Please install awscli to use S3 download.")

    # Prepare S3 object key
    s3_prefix = config.get('s3_prefix', '').rstrip('/')
    if s3_prefix:
        s3_key = s3_prefix + '/' + filename
    else:
        s3_key = filename

    s3_uri = 's3://%s/%s' % (config['s3_bucket'], s3_key)

    # Destination path
    destination_path = os.path.join(destination_dir, filename)

    # Set up environment variables for AWS credentials
    env = os.environ.copy()
    env['AWS_ACCESS_KEY_ID'] = config['s3_access_key']
    env['AWS_SECRET_ACCESS_KEY'] = config['s3_secret_key']

    # Build AWS CLI command
    cmd = [
        'aws', 's3', 'cp',
        s3_uri,
        destination_path,
        '--endpoint-url', config['s3_endpoint']
    ]

    print ("  Downloading from S3: %s" % s3_uri)

    # Retry logic for S3 download
    def download_operation():
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True, timeout=300)
            return result
        except subprocess.CalledProcessError as e:
            # Treat S3 download failures as network errors that should be retried
            raise socket.error("S3 download failed: %s" % e.stderr)
        except subprocess.TimeoutExpired:
            raise socket.timeout("S3 download timed out")

    try:
        retry_on_network_error(
            download_operation,
            max_retries=3,
            operation_name="S3 download %s" % filename
        )
        print ("  Download complete")
        return destination_path
    except Exception as e:
        raise Exception("S3 download failed after retries: %s" % str(e))


def upload_to_s3(file_path, config):
    """Upload a file to S3-compatible storage using AWS CLI with retry logic"""
    # Check if aws CLI is available
    try:
        subprocess.run(['aws', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise Exception("AWS CLI not found. Please install awscli to use S3 upload.")

    # Prepare S3 object key
    filename = os.path.basename(file_path)
    s3_prefix = config.get('s3_prefix', '').rstrip('/')
    if s3_prefix:
        s3_key = s3_prefix + '/' + filename
    else:
        s3_key = filename

    s3_uri = 's3://%s/%s' % (config['s3_bucket'], s3_key)

    # Set up environment variables for AWS credentials
    env = os.environ.copy()
    env['AWS_ACCESS_KEY_ID'] = config['s3_access_key']
    env['AWS_SECRET_ACCESS_KEY'] = config['s3_secret_key']

    # Build AWS CLI command
    cmd = [
        'aws', 's3', 'cp',
        file_path,
        s3_uri,
        '--endpoint-url', config['s3_endpoint']
    ]

    print ("  Uploading to S3: %s" % s3_uri)

    # Retry logic for S3 upload
    def upload_operation():
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True, timeout=300)
            return result
        except subprocess.CalledProcessError as e:
            # Treat S3 upload failures as network errors that should be retried
            raise socket.error("S3 upload failed: %s" % e.stderr)
        except subprocess.TimeoutExpired:
            raise socket.timeout("S3 upload timed out")

    try:
        retry_on_network_error(
            upload_operation,
            max_retries=3,
            operation_name="S3 upload %s" % filename
        )
        print ("  Upload complete")
        return True
    except Exception as e:
        raise Exception("S3 upload failed after retries: %s" % str(e))


def upload_messages(server, foldername, filename, messages_to_upload, nospinner, basedir):
    """Upload messages from mbox file to IMAP folder

    Returns:
        tuple: (uploaded_count, failed_count, total_bytes)
    """
    fullname = os.path.join(basedir, filename)
    uploaded = 0
    failed = 0
    total_size = 0

    # Check if file exists
    if not os.path.exists(fullname):
        print ("File %s: not found, skipping" % filename)
        return (0, len(messages_to_upload), 0)

    # nothing to do
    if not len(messages_to_upload):
        print ("Messages to upload: 0")
        return (0, 0, 0)

    total_messages = len(messages_to_upload)
    spinner = Spinner("Uploading messages to %s" % foldername,
                      nospinner, total=total_messages)

    try:
        # Open the mbox file
        try:
            mbox = mailbox.mbox(fullname)
        except (IOError, OSError) as e:
            spinner.stop()
            print ("\nERROR: Cannot open mbox file %s: %s" % (fullname, str(e)))
            return (0, len(messages_to_upload), 0)
        except Exception as e:
            spinner.stop()
            print ("\nERROR: Mailbox file %s is corrupted or invalid: %s" % (fullname, str(e)))
            return (0, len(messages_to_upload), 0)

        # Iterate through messages in the mbox file
        msg_index = 0
        try:
            for message in mbox:
                try:
                    # Get the Message-Id
                    try:
                        msg_id = message.get('Message-Id', '').strip()
                    except Exception as e:
                        print ("\nWARNING: Cannot read Message-Id from message: %s" % str(e))
                        failed += 1
                        continue

                    # Check if this message needs to be uploaded
                    if msg_id in messages_to_upload:
                        msg_index += 1
                        spinner.update(current=msg_index)
                        # Convert message to string (bytes)
                        try:
                            msg_bytes = bytes(str(message), 'utf-8')
                        except Exception as e:
                            print ("\nERROR: Cannot convert message %s to bytes: %s" % (msg_id, str(e)))
                            failed += 1
                            continue

                        # Upload to IMAP server with retry logic
                        # Use APPEND command to add message to folder
                        try:
                            foldername_quoted = '"{}"'.format(foldername)

                            # APPEND the message with retry
                            def append_operation():
                                return server.append(foldername_quoted, None, None, msg_bytes)

                            result = retry_on_network_error(
                                append_operation,
                                operation_name="Upload message %s" % msg_id
                            )

                            if result[0] == 'OK':
                                uploaded += 1
                                total_size += len(msg_bytes)
                            else:
                                print ("\nWARNING: Failed to upload message with ID %s: %s" % (msg_id, result))
                                failed += 1

                        except (imaplib.IMAP4.error, socket.error, socket.timeout) as e:
                            print ("\nERROR: Network error uploading message %s after retries: %s" % (msg_id, str(e)))
                            failed += 1
                        except Exception as e:
                            print ("\nERROR: Unexpected error uploading message %s: %s" % (msg_id, str(e)))
                            failed += 1

                except Exception as e:
                    print ("\nERROR: Error processing message for upload: %s" % str(e))
                    failed += 1

        except Exception as e:
            spinner.stop()
            print ("\nERROR: Error reading messages from mbox: %s" % str(e))
            try:
                mbox.close()
            except:
                pass
            return (uploaded, len(messages_to_upload) - uploaded, total_size)

        try:
            mbox.close()
        except Exception as e:
            print ("\nWARNING: Error closing mbox file %s: %s" % (filename, str(e)))

        spinner.stop()

        if failed > 0:
            print (": %s uploaded, %s total (%d failed)" % (uploaded, pretty_byte_count(total_size), failed))
        else:
            print (": %s uploaded, %s total" % (uploaded, pretty_byte_count(total_size)))

        return (uploaded, failed, total_size)

    except Exception as e:
        spinner.stop()
        print ("\nERROR: Fatal error in upload_messages: %s" % str(e))
        return (uploaded, len(messages_to_upload) - uploaded, total_size)


def download_messages(server, filename, messages, overwrite, nospinner, thunderbird, basedir, icloud):
    """Download messages from folder and append to mailbox

    Returns:
        tuple: (success_count, failed_count, total_bytes)
    """
    fullname = os.path.join(basedir,filename)

    success_count = 0
    failed_count = 0
    total = 0
    biggest = 0

    try:
        if overwrite and os.path.exists(fullname):
            print ("Deleting mbox: {0} at: {1}".format(filename,fullname))
            try:
                os.remove(fullname)
            except OSError as e:
                print ("ERROR: Cannot delete file %s: %s" % (fullname, str(e)))
                return (0, len(messages), 0)

        # Open disk file for append in binary mode
        try:
            mbox = open(fullname, 'ab')
        except IOError as e:
            print ("ERROR: Cannot open file %s for writing: %s" % (fullname, str(e)))
            return (0, len(messages), 0)

        # nothing to do
        if not len(messages):
            print ("New messages: 0")
            mbox.close()
            return (0, 0, 0)

        total_messages = len(messages)
        spinner = Spinner("Downloading messages to %s" % filename,
                          nospinner, total=total_messages)
        from_re = re.compile(b"\n(>*)From ")

        # each new message
        msg_index = 0
        for msg_id in messages.keys():
            msg_index += 1
            spinner.update(current=msg_index)
            try:
                # This "From" and the terminating newline below delimit messages
                # in mbox files.  Note that RFC 4155 specifies that the date be
                # in the same format as the output of ctime(3), which is required
                # by ISO C to use English day and month abbreviations.
                buf = "From nobody %s\n" % time.ctime()
                # If this is one of our synthesised Message-IDs, insert it before
                # the other headers
                if UUID in msg_id:
                    buf = buf + "Message-Id: %s\n" % msg_id

                # convert to bytes before writing to file of type binary
                buf_bytes=bytes(buf,'utf-8')
                mbox.write(buf_bytes)

                # fetch message with retry logic
                msg_id_str = str(messages[msg_id])
                try:
                    def fetch_operation():
                        return server.fetch(msg_id_str, "(BODY.PEEK[])" if icloud else "(RFC822)")

                    typ, data = retry_on_network_error(
                        fetch_operation,
                        operation_name="Fetch message %s" % msg_id_str
                    )
                except (imaplib.IMAP4.error, socket.error, socket.timeout) as e:
                    print ("\nWARNING: Failed to fetch message %s after retries: %s" % (msg_id_str, str(e)))
                    failed_count += 1
                    continue

                if typ != 'OK' or not data or not data[0]:
                    print ("\nWARNING: FETCH returned unexpected response for message %s" % msg_id_str)
                    failed_count += 1
                    continue

                try:
                    data_bytes = data[0][1]
                except (IndexError, TypeError) as e:
                    print ("\nWARNING: Cannot extract data from message %s: %s" % (msg_id_str, str(e)))
                    failed_count += 1
                    continue

                text_bytes = data_bytes.strip().replace(b'\r', b'')
                if thunderbird:
                    # This avoids Thunderbird mistaking a line starting "From  " as the start
                    # of a new message. _Might_ also apply to other mail lients - unknown
                    text_bytes = text_bytes.replace(b"\nFrom ", b"\n From ")
                else:
                    # Perform >From quoting as described by RFC 4155 and the qmail docs.
                    # https://www.rfc-editor.org/rfc/rfc4155.txt
                    # http://qmail.org/qmail-manual-html/man5/mbox.html
                    text_bytes = from_re.sub(b"\n>\\1From ", text_bytes)

                try:
                    mbox.write(text_bytes)
                    mbox.write(b'\n\n')
                except IOError as e:
                    print ("\nERROR: Failed to write message %s to disk: %s" % (msg_id_str, str(e)))
                    failed_count += 1
                    continue

                size = len(text_bytes)
                biggest = max(size, biggest)
                total += size
                success_count += 1

                del data
                gc.collect()

            except Exception as e:
                # Catch-all for unexpected errors
                print ("\nERROR: Unexpected error processing message %s: %s" % (msg_id, str(e)))
                failed_count += 1

        mbox.close()
        spinner.stop()

        if failed_count > 0:
            print (": %s total, %s for largest message (%d succeeded, %d failed)" %
                   (pretty_byte_count(total), pretty_byte_count(biggest), success_count, failed_count))
        else:
            print (": %s total, %s for largest message" % (pretty_byte_count(total),
                                                          pretty_byte_count(biggest)))

        return (success_count, failed_count, total)

    except Exception as e:
        print ("ERROR: Fatal error in download_messages for %s: %s" % (filename, str(e)))
        return (success_count, len(messages) - success_count, total)


def scan_file(filename, overwrite, nospinner, basedir):
    """Gets IDs of messages in the specified mbox file

    Returns:
        dict: Dictionary of message IDs found in file, or empty dict on error
    """
    # file will be overwritten
    if overwrite:
        return {}

    fullname = os.path.join(basedir,filename)

    # file doesn't exist
    if not os.path.exists(fullname):
        print ("File %s: not found" % filename)
        return {}

    spinner = Spinner("File %s" % filename, nospinner)
    messages = {}

    try:
        # open the mailbox file for read
        try:
            mbox = mailbox.mbox(fullname)
        except (IOError, OSError) as e:
            spinner.stop()
            print ("\nERROR: Cannot open mbox file %s: %s" % (fullname, str(e)))
            return {}
        except Exception as e:
            spinner.stop()
            print ("\nERROR: Mailbox file %s is corrupted or invalid: %s" % (fullname, str(e)))
            return {}

        # each message
        i = 0
        HEADER_MESSAGE_ID='Message-Id'

        try:
            for message in mbox:
                try:
                    header = ''
                    # We assume all messages on disk have message-ids
                    try:
                        header = "{0}: {1}".format(HEADER_MESSAGE_ID,message.get(HEADER_MESSAGE_ID))
                    except KeyError:
                        # No message ID was found. Warn the user and move on
                        print ("\nWARNING: Message #%d in %s has no {0} header.".format(HEADER_MESSAGE_ID) % (i, filename))
                        i += 1
                        spinner.spin()
                        continue
                    except Exception as e:
                        print ("\nWARNING: Cannot read headers from message #%d in %s: %s" % (i, filename, str(e)))
                        i += 1
                        spinner.spin()
                        continue

                    header = BLANKS_RE.sub(' ', header.strip())
                    try:
                        msg_id = MSGID_RE.match(header).group(1)
                        if msg_id not in messages.keys():
                            # avoid adding dupes
                            messages[msg_id] = msg_id
                    except (AttributeError, IndexError):
                        # Message-Id was found but could somehow not be parsed by regexp
                        print ("\nWARNING: Message #%d in %s has a malformed {0} header.".format(HEADER_MESSAGE_ID) % (i, filename))

                except Exception as e:
                    # Catch-all for unexpected errors processing individual message
                    print ("\nWARNING: Error processing message #%d in %s: %s" % (i, filename, str(e)))

                spinner.spin()
                i = i + 1

        except Exception as e:
            # Error iterating through mailbox
            spinner.stop()
            print ("\nERROR: Failed while reading mailbox %s: %s" % (filename, str(e)))
            print ("Recovered %d messages before error" % len(messages))
            try:
                mbox.close()
            except:
                pass
            return messages

        # done
        try:
            mbox.close()
        except Exception as e:
            print ("\nWARNING: Error closing mbox file %s: %s" % (filename, str(e)))

        spinner.stop()
        print (": %d messages" % (len(messages.keys())))
        return messages

    except Exception as e:
        spinner.stop()
        print ("\nERROR: Fatal error in scan_file for %s: %s" % (filename, str(e)))
        return {}


def scan_folder(server, foldername, nospinner):
    """Gets IDs of messages in the specified folder, returns id:num dict

    Returns:
        dict: Dictionary mapping message IDs to message numbers, or empty dict on error

    Raises:
        SkipFolderException: When folder cannot be accessed (to allow continuing with next folder)
    """
    messages = {}
    foldername_quoted = '"{}"'.format(foldername)
    spinner = None  # Will be initialized after we know num_msgs

    try:
        # Select the folder with retry logic
        try:
            def select_operation():
                return server.select(foldername_quoted, readonly=True)

            typ, data = retry_on_network_error(
                select_operation,
                operation_name="Select folder %s" % foldername_quoted
            )
        except (imaplib.IMAP4.error, socket.error, socket.timeout) as e:
            raise SkipFolderException("SELECT failed for %s after retries: %s" % (foldername_quoted, str(e)))
        except Exception as e:
            raise SkipFolderException("Unexpected error selecting folder %s: %s" % (foldername_quoted, str(e)))

        if 'OK' != typ:
            raise SkipFolderException("SELECT failed: %s" % data)

        try:
            num_msgs = int(data[0])
        except (ValueError, IndexError, TypeError) as e:
            raise SkipFolderException("Cannot parse message count for %s: %s" % (foldername_quoted, str(e)))

        # Initialize spinner with total message count for progress tracking
        spinner = Spinner("Folder %s" % foldername_quoted, nospinner, total=num_msgs)

        # Retrieve Message-Id headers in batches to avoid memory issues with large mailboxes
        # Process messages in batches of FETCH_BATCH_SIZE to keep memory usage constant
        if num_msgs > 0:
            # Process messages in batches
            for batch_start in range(1, num_msgs + 1, FETCH_BATCH_SIZE):
                batch_end = min(batch_start + FETCH_BATCH_SIZE - 1, num_msgs)
                batch_range = '%d:%d' % (batch_start, batch_end)

                # Fetch headers for this batch
                # The result is an array of result tuples with a terminating closing parenthesis
                # after each tuple. That means that the first result is at index 0, the second at
                # 2, third at 4, and so on.
                try:
                    def fetch_headers_operation():
                        return server.fetch(batch_range, '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])')

                    typ, data = retry_on_network_error(
                        fetch_headers_operation,
                        operation_name="Fetch headers %s from %s" % (batch_range, foldername_quoted)
                    )
                except (imaplib.IMAP4.error, socket.error, socket.timeout) as e:
                    spinner.stop()
                    raise SkipFolderException("FETCH failed for %s after retries: %s" % (foldername_quoted, str(e)))
                except Exception as e:
                    spinner.stop()
                    raise SkipFolderException("Unexpected error fetching headers from %s: %s" % (foldername_quoted, str(e)))

                if 'OK' != typ:
                    spinner.stop()
                    raise SkipFolderException("FETCH failed: %s" % (data))

                # Process each message in this batch
                batch_size = batch_end - batch_start + 1
                for i in range(0, batch_size):
                    num = batch_start + i
                    spinner.update(current=num)

                    try:
                        # Double the index because of the terminating parenthesis after each tuple.
                        data_str = str(data[2 * i][1], 'utf-8', 'replace')
                        header = data_str.strip()

                        # remove newlines inside Message-Id (a dumb Exchange trait)
                        header = BLANKS_RE.sub(' ', header)
                        try:
                            msg_id = MSGID_RE.match(header).group(1)
                            if msg_id not in messages.keys():
                                # avoid adding dupes
                                messages[msg_id] = num
                        except (IndexError, AttributeError):
                            # Some messages may have no Message-Id, so we'll synthesise one
                            # (this usually happens with Sent, Drafts and .Mac news)
                            try:
                                msg_typ, msg_data = server.fetch(
                                    str(num), '(BODY[HEADER.FIELDS (FROM TO CC DATE SUBJECT)])')
                            except (imaplib.IMAP4.error, socket.error, socket.timeout) as e:
                                print ("\nWARNING: Cannot fetch headers for message %d: %s" % (num, str(e)))
                                continue
                            except Exception as e:
                                print ("\nWARNING: Unexpected error fetching message %d: %s" % (num, str(e)))
                                continue

                            if 'OK' != msg_typ:
                                print ("\nWARNING: FETCH %d failed: %s" % (num, msg_data))
                                continue

                            try:
                                data_str = str(msg_data[0][1], 'utf-8', 'replace')
                                header = data_str.strip()
                                header = header.replace('\r\n', '\t').encode('utf-8')
                                messages['<' + UUID + '.' +
                                         hashlib.sha1(header).hexdigest() + '>'] = num
                            except Exception as e:
                                print ("\nWARNING: Cannot generate message ID for message %d: %s" % (num, str(e)))

                    except (IndexError, KeyError, TypeError) as e:
                        print ("\nWARNING: Cannot process message %d in %s: %s" % (num, foldername_quoted, str(e)))
                    except Exception as e:
                        print ("\nWARNING: Unexpected error processing message %d: %s" % (num, str(e)))

                # Free up memory from this batch before processing the next one
                del data
                gc.collect()

    except SkipFolderException:
        # Re-raise SkipFolderException to allow caller to continue with next folder
        raise
    except Exception as e:
        if spinner:
            spinner.stop()
        print ("\nERROR: Fatal error in scan_folder for %s: %s" % (foldername_quoted, str(e)))
        raise SkipFolderException("Fatal error scanning folder: %s" % str(e))
    finally:
        if spinner:
            spinner.stop()
        print (":",)

    # done
    print ("%d messages" % (len(messages.keys())))
    return messages


def parse_paren_list(row):
    """Parses the nested list of attributes at the start of a LIST response"""
    # eat starting paren
    assert(row[0] == '(')
    row = row[1:]

    result = []

    # NOTE: RFC3501 doesn't fully define the format of name attributes
    name_attrib_re = re.compile(r"^\s*(\\[a-zA-Z0-9_]+)\s*")

    # eat name attributes until ending paren
    while row[0] != ')':
        # recurse
        if row[0] == '(':
            paren_list, row = parse_paren_list(row)
            result.append(paren_list)
        # consume name attribute
        else:
            match = name_attrib_re.search(row)
            assert(match is not None)
            name_attrib = row[match.start():match.end()]
            row = row[match.end():]
            name_attrib = name_attrib.strip()
            result.append(name_attrib)

    # eat ending paren
    assert(')' == row[0])
    row = row[1:]

    # done!
    return result, row


def parse_string_list(row):
    """Parses the quoted and unquoted strings at the end of a LIST response"""
    slist = re.compile(r'\s*"([^"]+)"\s*|\s*(\S+)\s*').split(row)
    return [s for s in slist if s]


def parse_list(row):
    """Parses response of LIST command into a list"""
    row = row.strip()
    print(row)
    paren_list, row = parse_paren_list(row)
    string_list = parse_string_list(row)
    assert(len(string_list) == 2)
    return [paren_list] + string_list


def get_names(server, thunderbird, nospinner):
    """Get list of folders, returns [(FolderName,FileName)]"""
    spinner = Spinner("Finding Folders", nospinner)

    # Get LIST of all folders
    typ, data = server.list()
    assert(typ == 'OK')
    spinner.spin()

    names = []

    # parse each LIST entry for folder name hierarchy delimiter
    for row in data:
        row_str = str(row,'utf-8')
        lst = parse_list(row_str) # [attribs, hierarchy delimiter, root name]
        delim = lst[1]
        foldername = lst[2]
        if thunderbird:
            filename = '.sbd/'.join(foldername.split(delim))
            if filename.startswith("INBOX"):
                filename = filename.replace("INBOX", "Inbox")
        else:
            filename = '.'.join(foldername.split(delim)) + '.mbox'
        # print "\n*** Folder:", foldername # *DEBUG
        # print "***   File:", filename # *DEBUG
        names.append((foldername, filename))

    # done
    spinner.stop()
    print (": %s folders" % (len(names)))
    return names


def load_config_file(config_file):
    """Load configuration from YAML file"""
    if not HAS_YAML:
        print ("ERROR: PyYAML is required for config file support.")
        print ("Install with: pip install pyyaml")
        sys.exit(2)

    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        if not config_data or 'accounts' not in config_data:
            print ("ERROR: Invalid config file. Must contain 'accounts' section.")
            sys.exit(2)

        return config_data

    except FileNotFoundError:
        print ("ERROR: Config file not found: %s" % config_file)
        sys.exit(2)
    except yaml.YAMLError as e:
        print ("ERROR: Invalid YAML in config file: %s" % str(e))
        sys.exit(2)
    except Exception as e:
        print ("ERROR: Failed to load config file: %s" % str(e))
        sys.exit(2)


def parse_account_config(account, global_config, date_override=None):
    """Parse a single account configuration, merging with global settings

    Args:
        account: Account configuration dict
        global_config: Global configuration dict
        date_override: Optional date string to override date folder (for selective restore)
    """
    config = {}

    # Account name (required)
    if 'name' not in account:
        print ("ERROR: Account missing 'name' field")
        sys.exit(2)

    account_name = account['name']
    config['account_name'] = account_name

    # Server settings
    config['server'] = account.get('server')
    config['user'] = account.get('user')

    # Password handling
    pass_value = account.get('pass', '')
    if pass_value.startswith('env:'):
        # Read from environment variable
        env_var = pass_value[4:]
        config['pass'] = os.environ.get(env_var, '')
        if not config['pass']:
            print ("ERROR: Environment variable '%s' not set for account '%s'" % (env_var, account_name))
            sys.exit(2)
    else:
        # Use string_from_file to handle @file syntax
        try:
            config['pass'] = string_from_file(pass_value) if pass_value else ''
        except Exception as ex:
            print ("ERROR: Can't read password for account '%s': %s" % (account_name, str(ex)))
            sys.exit(2)

    # Port (optional)
    if 'port' in account:
        config['port'] = account['port']

    # SSL setting (default from global or account-specific)
    config['usessl'] = account.get('ssl', global_config.get('ssl', True))

    # Timeout (default from global or account-specific)
    config['timeout'] = account.get('timeout', global_config.get('timeout', 60))

    # Base directory - create account subdirectory
    global_basedir = global_config.get('basedir', './backups')

    # Check if date-based folders are enabled
    use_date_folders = account.get('use_date_folders', global_config.get('use_date_folders', False))

    if use_date_folders or date_override:
        # Get date format (default: YYYY-MM-DD)
        date_format = account.get('date_format', global_config.get('date_format', '%Y-%m-%d'))
        # Use override date if provided, otherwise use current date
        if date_override:
            date_str = date_override
        else:
            date_str = time.strftime(date_format)
        # Add date to the path: basedir/account_name/{date}/
        config['basedir'] = os.path.join(global_basedir, account_name, date_str)
    else:
        # Standard path: basedir/account_name/
        config['basedir'] = os.path.join(global_basedir, account_name)

    # Folders
    if 'folders' in account:
        config['folders'] = account['folders']
    if 'exclude_folders' in account:
        config['exclude-folders'] = account['exclude_folders']

    # Spinner setting
    config['nospinner'] = account.get('nospinner', global_config.get('nospinner', False))

    # Thunderbird and iCloud settings
    config['thunderbird'] = account.get('thunderbird', global_config.get('thunderbird', False))
    config['icloud'] = account.get('icloud', global_config.get('icloud', False))

    # Restore mode (default False)
    config['restore'] = False
    config['overwrite'] = False

    # S3 configuration
    s3_config = {}
    global_s3 = global_config.get('s3', {})
    account_s3 = account.get('s3', {})

    # Check if S3 is enabled for this account
    s3_enabled = account.get('s3_enabled', account_s3.get('enabled', global_s3.get('enabled', False)))
    config['s3_upload'] = s3_enabled

    if s3_enabled:
        # Merge S3 settings (account overrides global)
        config['s3_endpoint'] = account_s3.get('endpoint', global_s3.get('endpoint', ''))
        config['s3_bucket'] = account_s3.get('bucket', global_s3.get('bucket', ''))
        config['s3_access_key'] = account_s3.get('access_key', global_s3.get('access_key', ''))
        config['s3_secret_key'] = account_s3.get('secret_key', global_s3.get('secret_key', ''))

        # S3 prefix: use custom or build from global prefix + account name (+ date if enabled)
        if 's3_prefix' in account:
            config['s3_prefix'] = account['s3_prefix']
        elif 's3_prefix' in account_s3:
            config['s3_prefix'] = account_s3['prefix']
        else:
            global_prefix = global_s3.get('prefix', 'backups')
            if use_date_folders or date_override:
                # Include date in S3 prefix: prefix/account_name/{date}
                date_format = account.get('date_format', global_config.get('date_format', '%Y-%m-%d'))
                # Use override date if provided, otherwise use current date
                if date_override:
                    date_str = date_override
                else:
                    date_str = time.strftime(date_format)
                config['s3_prefix'] = '%s/%s/%s' % (global_prefix.rstrip('/'), account_name, date_str)
            else:
                # Standard prefix: prefix/account_name
                config['s3_prefix'] = '%s/%s' % (global_prefix.rstrip('/'), account_name)

    # GPG configuration
    global_gpg = global_config.get('gpg', {})
    account_gpg = account.get('gpg', {})

    # Check if GPG is enabled for this account
    gpg_enabled = account.get('gpg_enabled', account_gpg.get('enabled', global_gpg.get('enabled', False)))
    config['gpg_encrypt'] = gpg_enabled

    if gpg_enabled:
        # Merge GPG settings (account overrides global)
        config['gpg_recipient'] = account_gpg.get('recipient', global_gpg.get('recipient', ''))
        import_key = account_gpg.get('import_key', global_gpg.get('import_key', ''))
        if import_key:
            config['gpg_import_key'] = import_key

    return config


def print_usage():
    """Prints usage, exits"""
    #     "                                                                               "
    print ("Usage: imapbackup [OPTIONS] -s HOST -u USERNAME [-p PASSWORD]")
    print ("   or: imapbackup --config=CONFIG_FILE [--restore]")
    print ("   or: imapbackup")
    print ("")
    print ("Config File Mode:")
    print (" --config=FILE                 Load settings from YAML config file.")
    print ("                               Allows backing up multiple accounts.")
    print ("                               See config.example.yaml for format.")
    print ("")
    print (" Auto-detection:               If no arguments are provided, the script")
    print ("                               automatically looks for 'config.yaml' or")
    print ("                               'config.yml' in the current directory.")
    print ("")
    print (" --restore                     Restore mode (use with --config).")
    print (" --account=NAME                Filter to specific account(s). Can be comma-separated")
    print ("                               or specified multiple times.")
    print ("                               Example: --account=gmail,work")
    print (" --date=DATE                   Override date for restore. Useful for restoring")
    print ("                               from a specific date-based backup folder.")
    print ("                               Example: --date=2025-10-10")
    print (" --list                        List all available backups (local and S3).")
    print ("                               Can be combined with --account to filter.")
    print ("")
    print ("Command Line Mode:")
    print (" -d DIR --mbox-dir=DIR         Write mbox files to directory. (defaults to cwd)")
    print (" -a --append-to-mboxes         Append new messages to mbox files. (default)")
    print (" -y --yes-overwrite-mboxes     Overwite existing mbox files instead of appending.")
    print (" -r --restore                  Restore mode: upload mbox files to IMAP server.")
    print ("                               Will not upload messages that already exist on server.")
    print (" -f FOLDERS --folders=FOLDERS  Specify which folders to include. Comma separated list.")
    print (" --exclude-folders=FOLDERS     Specify which folders to exclude. Comma separated list.")
    print ("                               You cannot use both --folders and --exclude-folders.")
    print (" -e --ssl                      Use SSL.  Port defaults to 993.")
    print (" -k KEY --key=KEY              PEM private key file for SSL.  Specify cert, too.")
    print (" -c CERT --cert=CERT           PEM certificate chain for SSL.  Specify key, too.")
    print ("                               Python's SSL module doesn't check the cert chain.")
    print (" -s HOST --server=HOST         Address of server, port optional, eg. mail.com:143")
    print (" -u USER --user=USER           Username to log into server")
    print (" -p PASS --pass=PASS           Prompts for password if not specified.  If the first")
    print ("                               character is '@', treat the rest as a path to a file")
    print ("                               containing the password.  Leading '\' makes it literal.")
    print (" -t SECS --timeout=SECS        Sets socket timeout to SECS seconds.")
    print (" --thunderbird                 Create Mozilla Thunderbird compatible mailbox")
    print (" --nospinner                   Disable spinner (makes output log-friendly)")
    print (" --icloud                      Enable iCloud compatibility mode (for iCloud mailserver)")
    print ("")
    print ("S3 Storage Options:")
    print (" --s3-upload                   Enable S3 storage integration")
    print ("                               Backup mode: Upload mbox files to S3 after backup")
    print ("                               Restore mode: Download mbox files from S3 before restore")
    print (" --s3-endpoint=URL             S3 endpoint URL (e.g., https://s3.eu-central-1.wasabisys.com)")
    print (" --s3-bucket=BUCKET            S3 bucket name")
    print (" --s3-access-key=KEY           S3 access key ID")
    print (" --s3-secret-key=KEY           S3 secret access key")
    print (" --s3-prefix=PREFIX            Optional prefix for S3 object keys (e.g., backups/imap/)")
    print (" --gpg-encrypt                 Encrypt/decrypt files with GPG when using S3")
    print ("                               Backup mode: Encrypts before upload")
    print ("                               Restore mode: Decrypts after download")
    print (" --gpg-recipient=EMAIL         GPG recipient email/key ID (required for encryption)")
    print (" --gpg-import-key=SOURCE       Import GPG public key before encryption. SOURCE can be:")
    print ("                               - File path: /path/to/key.asc or ~/keys/public.asc")
    print ("                               - URL: https://example.com/public-key.asc")
    print ("                               - Environment variable: env:GPG_PUBLIC_KEY")
    sys.exit(2)


def process_cline():
    """Uses getopt to process command line, returns (config, warnings, errors)"""
    # read command line
    try:
        short_args = "ayrnekt:c:s:u:p:f:d:"
        long_args = ["append-to-mboxes", "yes-overwrite-mboxes", "restore",
                     "ssl", "timeout", "keyfile=", "certfile=", "server=", "user=", "pass=",
                     "folders=", "exclude-folders=", "thunderbird", "nospinner", "mbox-dir=", "icloud",
                     "s3-upload", "s3-endpoint=", "s3-bucket=", "s3-access-key=", "s3-secret-key=",
                     "s3-prefix=", "gpg-encrypt", "gpg-recipient=", "gpg-import-key=", "config=",
                     "account=", "date=", "list"]
        opts, extraargs = getopt.getopt(sys.argv[1:], short_args, long_args)
    except getopt.GetoptError:
        print_usage()

    warnings = []
    config = {'overwrite': False, 'usessl': False,
              'thunderbird': False, 'nospinner': False,
              'basedir': ".", 'icloud': False, 'restore': False,
              's3_upload': False, 'gpg_encrypt': False}
    errors = []

    # empty command line - will be handled in get_config() to check for default config files
    # if not len(opts) and not len(extraargs):
    #     print_usage()

    # process each command line option, save in config
    for option, value in opts:
        if option in ("-d", "--mbox-dir"):
            config['basedir'] = value
        elif option in ("-a", "--append-to-mboxes"):
            config['overwrite'] = False
        elif option in ("-y", "--yes-overwrite-mboxes"):
            warnings.append("Existing mbox files will be overwritten!")
            config["overwrite"] = True
        elif option in ("-r", "--restore"):
            config['restore'] = True
        elif option in ("-e", "--ssl"):
            config['usessl'] = True
        elif option in ("-k", "--keyfile"):
            config['keyfilename'] = value
        elif option in ("-f", "--folders"):
            config['folders'] = value
        elif option in ("--exclude-folders"):
            config['exclude-folders'] = value
        elif option in ("-c", "--certfile"):
            config['certfilename'] = value
        elif option in ("-s", "--server"):
            config['server'] = value
        elif option in ("-u", "--user"):
            config['user'] = value
        elif option in ("-p", "--pass"):
            try:
                config['pass'] = string_from_file(value)
            except Exception as ex:
                errors.append("Can't read password: %s" % (str(ex)))
        elif option in ("-t", "--timeout"):
            config['timeout'] = value
        elif option == "--thunderbird":
            config['thunderbird'] = True
        elif option == "--nospinner":
            config['nospinner'] = True
        elif option == "--icloud":
            config['icloud'] = True
        elif option == "--s3-upload":
            config['s3_upload'] = True
        elif option == "--s3-endpoint":
            config['s3_endpoint'] = value
        elif option == "--s3-bucket":
            config['s3_bucket'] = value
        elif option == "--s3-access-key":
            config['s3_access_key'] = value
        elif option == "--s3-secret-key":
            config['s3_secret_key'] = value
        elif option == "--s3-prefix":
            config['s3_prefix'] = value
        elif option == "--gpg-encrypt":
            config['gpg_encrypt'] = True
        elif option == "--gpg-recipient":
            config['gpg_recipient'] = value
        elif option == "--gpg-import-key":
            config['gpg_import_key'] = value
        elif option == "--config":
            config['config_file'] = value
        elif option == "--account":
            # Store as comma-separated list (can be specified multiple times)
            if 'account_filter' not in config:
                config['account_filter'] = []
            # Split by comma and add all accounts
            accounts = [a.strip() for a in value.split(',') if a.strip()]
            config['account_filter'].extend(accounts)
        elif option == "--date":
            config['date_override'] = value
        elif option == "--list":
            config['list_backups'] = True
        else:
            errors.append("Unknown option: " + option)

    # don't ignore extra arguments
    for arg in extraargs:
        errors.append("Unknown argument: " + arg)

    # done processing command line
    return config, warnings, errors


def check_config(config, warnings, errors):
    """Checks the config for consistency, returns (config, warnings, errors)"""
    # Skip validation if using config file mode
    if 'config_file' in config:
        return config, warnings, errors

    if 'server' not in config:
        errors.append("No server specified.")
    if 'user' not in config:
        errors.append("No username specified.")
    if ('keyfilename' in config) ^ ('certfilename' in config):
        errors.append("Please specify both key and cert or neither.")
    if 'keyfilename' in config and not config['usessl']:
        errors.append("Key specified without SSL.  Please use -e or --ssl.")
    if 'certfilename' in config and not config['usessl']:
        errors.append(
            "Certificate specified without SSL.  Please use -e or --ssl.")

    # Check S3 configuration
    if config.get('s3_upload'):
        if 's3_endpoint' not in config:
            errors.append("S3 upload enabled but no --s3-endpoint specified.")
        if 's3_bucket' not in config:
            errors.append("S3 upload enabled but no --s3-bucket specified.")
        if 's3_access_key' not in config:
            errors.append("S3 upload enabled but no --s3-access-key specified.")
        if 's3_secret_key' not in config:
            errors.append("S3 upload enabled but no --s3-secret-key specified.")

    # Check GPG configuration
    if config.get('gpg_encrypt'):
        if not config.get('s3_upload'):
            warnings.append("GPG encryption enabled but S3 upload is not enabled.")
        if 'gpg_recipient' not in config:
            errors.append("GPG encryption enabled but no --gpg-recipient specified.")
    if 'server' in config and ':' in config['server']:
        # get host and port strings
        bits = config['server'].split(':', 1)
        config['server'] = bits[0]
        # port specified, convert it to int
        if len(bits) > 1 and len(bits[1]) > 0:
            try:
                port = int(bits[1])
                if port > 65535 or port < 0:
                    raise ValueError
                config['port'] = port
            except ValueError:
                errors.append(
                    "Invalid port.  Port must be an integer between 0 and 65535.")
    if 'timeout' in config:
        try:
            timeout = int(config['timeout'])
            if timeout <= 0:
                raise ValueError
            config['timeout'] = timeout
        except ValueError:
            errors.append(
                "Invalid timeout value.  Must be an integer greater than 0.")
    return config, warnings, errors


def get_config():
    """Gets config from command line and console, returns config"""
    # config = {
    #   'overwrite': True or False
    #   'server': String
    #   'port': Integer
    #   'user': String
    #   'pass': String
    #   'usessl': True or False
    #   'keyfilename': String or None
    #   'certfilename': String or None
    # }

    config, warnings, errors = process_cline()

    # If no config file specified and no command line arguments, check for default config files
    if 'config_file' not in config and not config.get('server') and not config.get('user'):
        # Check for default config files
        config_found = False
        for default_config in ['config.yaml', 'config.yml']:
            if os.path.exists(default_config):
                print ("No arguments provided. Using default config file: %s" % default_config)
                print ("")
                config['config_file'] = default_config
                config_found = True
                break

        # If no default config file found, show usage
        if not config_found:
            print_usage()

    config, warnings, errors = check_config(config, warnings, errors)

    # show warnings
    for warning in warnings:
        print ("WARNING:", warning)

    # show errors, exit
    for error in errors:
        print ("ERROR", error)
    if len(errors):
        sys.exit(2)

    # prompt for password, if necessary (only for command-line mode, not config file mode)
    if 'pass' not in config and 'config_file' not in config:
        config['pass'] = getpass.getpass()

    # defaults (only for command-line mode)
    if 'config_file' not in config:
        if 'port' not in config:
            if config['usessl']:
                config['port'] = 993
            else:
                config['port'] = 143
        if 'timeout' not in config:
            config['timeout'] = 60

    # done!
    return config


def connect_and_login(config):
    """Connects to the server and logs in with retry logic. Returns IMAP4 object."""
    assert(not (('keyfilename' in config) ^ ('certfilename' in config)))
    if config['timeout']:
        socket.setdefaulttimeout(config['timeout'])

    def connect_operation():
        """Connect and login to IMAP server"""
        if config['usessl'] and 'keyfilename' in config:
            print ("Connecting to '%s' TCP port %d," % (
                config['server'], config['port']),)
            print ("SSL, key from %s," % (config['keyfilename']),)
            print ("cert from %s " % (config['certfilename']))
            server = imaplib.IMAP4_SSL(config['server'], config['port'],
                                       config['keyfilename'], config['certfilename'])
        elif config['usessl']:
            print ("Connecting to '%s' TCP port %d, SSL" % (
                config['server'], config['port']))
            server = imaplib.IMAP4_SSL(config['server'], config['port'])
        else:
            print ("Connecting to '%s' TCP port %d" % (
                config['server'], config['port']))
            server = imaplib.IMAP4(config['server'], config['port'])

        # speed up interactions on TCP connections using small packets
        server.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        print ("Logging in as '%s'" % (config['user']))
        server.login(config['user'], config['pass'])
        return server

    try:
        # Retry connection with exponential backoff
        server = retry_on_network_error(
            connect_operation,
            max_retries=3,
            operation_name="Connect to %s" % config['server']
        )
        return server

    except socket.gaierror as e:
        (err, desc) = e
        print ("ERROR: problem looking up server '%s' (%s %s)" % (
            config['server'], err, desc))
        sys.exit(3)
    except socket.error as e:
        if str(e) == "SSL_CTX_use_PrivateKey_file error":
            print ("ERROR: error reading private key file '%s'" % (
                config['keyfilename']))
        elif str(e) == "SSL_CTX_use_certificate_chain_file error":
            print ("ERROR: error reading certificate chain file '%s'" % (
                config['keyfilename']))
        else:
            print ("ERROR: could not connect to '%s' after retries (%s)" % (
                config['server'], e))
        sys.exit(4)
    except imaplib.IMAP4.error as e:
        print ("ERROR: IMAP error after retries: %s" % str(e))
        sys.exit(4)



def list_backups(global_config, accounts, account_filter):
    """List available backups for accounts (from local filesystem and/or S3)

    Args:
        global_config: Global configuration dict
        accounts: List of account configurations
        account_filter: Optional list of account names to filter
    """
    # Filter accounts if requested
    if account_filter:
        accounts = [acc for acc in accounts if acc.get('name') in account_filter]
        if not accounts:
            print ("ERROR: No accounts matched the filter")
            return

    print ("=" * 70)
    print ("Available backups")
    print ("=" * 70)
    print ("")

    global_basedir = global_config.get('basedir', './backups')

    for account in accounts:
        account_name = account.get('name', 'unknown')
        print ("Account: %s" % account_name)
        print ("-" * 70)

        # Check if account uses date-based folders
        use_date_folders = account.get('use_date_folders', global_config.get('use_date_folders', False))

        account_path = os.path.join(global_basedir, account_name)

        # LOCAL FILESYSTEM
        local_backups = []
        if os.path.exists(account_path):
            if use_date_folders:
                # List date folders
                try:
                    entries = os.listdir(account_path)
                    for entry in sorted(entries, reverse=True):
                        entry_path = os.path.join(account_path, entry)
                        if os.path.isdir(entry_path):
                            # Count mbox files
                            mbox_files = [f for f in os.listdir(entry_path) if f.endswith('.mbox')]
                            if mbox_files:
                                local_backups.append({'date': entry, 'files': len(mbox_files), 'path': entry_path})
                except OSError as e:
                    pass
            else:
                # List mbox files directly
                try:
                    mbox_files = [f for f in os.listdir(account_path) if f.endswith('.mbox')]
                    if mbox_files:
                        local_backups.append({'date': 'N/A', 'files': len(mbox_files), 'path': account_path})
                except OSError as e:
                    pass

        if local_backups:
            print ("  Local backups:")
            for backup in local_backups:
                if backup['date'] == 'N/A':
                    print ("    %s (%d mbox files)" % (backup['path'], backup['files']))
                else:
                    print ("    Date: %s (%d mbox files)" % (backup['date'], backup['files']))
        else:
            print ("  Local backups: None found")

        # S3 BACKUPS
        global_s3 = global_config.get('s3', {})
        account_s3 = account.get('s3', {})
        s3_enabled = account.get('s3_enabled', account_s3.get('enabled', global_s3.get('enabled', False)))

        if s3_enabled:
            print ("  S3 backups:")
            s3_endpoint = account_s3.get('endpoint', global_s3.get('endpoint', ''))
            s3_bucket = account_s3.get('bucket', global_s3.get('bucket', ''))
            s3_access_key = account_s3.get('access_key', global_s3.get('access_key', ''))
            s3_secret_key = account_s3.get('secret_key', global_s3.get('secret_key', ''))
            global_prefix = global_s3.get('prefix', 'backups')

            # Build S3 prefix for this account
            if use_date_folders:
                # List all date folders in S3
                s3_prefix = '%s/%s/' % (global_prefix.rstrip('/'), account_name)
            else:
                s3_prefix = '%s/%s/' % (global_prefix.rstrip('/'), account_name)

            try:
                # Use AWS CLI to list objects
                env = os.environ.copy()
                env['AWS_ACCESS_KEY_ID'] = s3_access_key
                env['AWS_SECRET_ACCESS_KEY'] = s3_secret_key

                cmd = [
                    'aws', 's3', 'ls',
                    's3://%s/%s' % (s3_bucket, s3_prefix),
                    '--endpoint-url', s3_endpoint,
                    '--recursive'
                ]

                result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

                if result.returncode == 0 and result.stdout.strip():
                    # Parse output
                    lines = result.stdout.strip().split('\n')
                    s3_backups = {}

                    for line in lines:
                        # Parse line format: "2025-10-10 14:30:00   12345  path/to/file"
                        parts = line.split()
                        if len(parts) >= 4:
                            s3_key = ' '.join(parts[3:])
                            # Extract date from path if present
                            if use_date_folders:
                                # Extract date folder from path
                                # Format: prefix/account_name/YYYY-MM-DD/file.mbox
                                path_parts = s3_key.split('/')
                                if len(path_parts) >= 3:
                                    date_folder = path_parts[-2]
                                    if date_folder not in s3_backups:
                                        s3_backups[date_folder] = 0
                                    if s3_key.endswith('.mbox') or s3_key.endswith('.mbox.gpg'):
                                        s3_backups[date_folder] += 1
                            else:
                                # No date folders
                                if 'latest' not in s3_backups:
                                    s3_backups['latest'] = 0
                                if s3_key.endswith('.mbox') or s3_key.endswith('.mbox.gpg'):
                                    s3_backups['latest'] += 1

                    if s3_backups:
                        for date, count in sorted(s3_backups.items(), reverse=True):
                            if date == 'latest':
                                print ("    %d mbox files in s3://%s/%s" % (count, s3_bucket, s3_prefix))
                            else:
                                print ("    Date: %s (%d mbox files) in s3://%s/%s%s/" % (date, count, s3_bucket, s3_prefix, date))
                    else:
                        print ("    None found")
                else:
                    print ("    Unable to list (check S3 credentials and permissions)")

            except Exception as e:
                print ("    Error listing S3: %s" % str(e))

        print ("")


def create_basedir(basedir):
    """ Create the base directory on disk """
    if os.path.isdir(basedir):
        return

    try:
        os.makedirs(basedir)
    except OSError as e:
        raise



def create_folder_structure(names,basedir):
    """ Create the folder structure on disk """
    for imap_foldername, filename in sorted(names):
        disk_foldername = os.path.split(filename)[0]
        if disk_foldername:
            try:
                # print "*** makedirs:", disk_foldername  # *DEBUG
                disk_path = os.path.join(basedir,disk_foldername)
                os.makedirs(disk_path)
            except OSError as e:
                if e.errno != 17:
                    raise


def process_account(config):
    """Process a single account for backup or restore"""
    # Validate required fields
    if 'server' not in config or 'user' not in config:
        print ("ERROR: Account config missing required fields (server, user)")
        return False

    # Set port defaults if not specified
    if 'port' not in config:
        if config.get('usessl', True):
            config['port'] = 993
        else:
            config['port'] = 143

    # Set timeout default if not specified
    if 'timeout' not in config:
        config['timeout'] = 60

    # Connect to server
    try:
        server = connect_and_login(config)
    except Exception as e:
        print ("ERROR: Failed to connect to account '%s': %s" % (config.get('account_name', 'unknown'), str(e)))
        return False

    # Get folder names
    names = get_names(server, config.get('thunderbird', False), config.get('nospinner', False))

    # Filter folders
    exclude_folders = []
    if config.get('folders') and config.get('exclude-folders'):
        print ("ERROR: Cannot use both 'folders' and 'exclude_folders' for account '%s'" % config.get('account_name', 'unknown'))
        server.logout()
        return False

    if config.get('folders'):
        # Handle both string (comma-separated) and already-split list
        if isinstance(config['folders'], str):
            dirs = list(map(lambda x: x.strip(), config['folders'].split(',')))
        else:
            dirs = config['folders'] if isinstance(config['folders'], list) else [config['folders']]

        if config.get('thunderbird', False):
            dirs = [i.replace("Inbox", "INBOX", 1) if i.startswith("Inbox") else i for i in dirs]
        names = list(filter(lambda x: x[0] in dirs, names))
    elif config.get('exclude-folders'):
        # Handle both string (comma-separated) and already-split list
        if isinstance(config['exclude-folders'], str):
            exclude_folders = list(map(lambda x: x.strip(), config['exclude-folders'].split(',')))
        else:
            exclude_folders = config['exclude-folders'] if isinstance(config['exclude-folders'], list) else [config['exclude-folders']]

    # Setup base directory
    basedir = config.get('basedir', '.')
    if basedir.startswith('~'):
        basedir = os.path.expanduser(basedir)
    else:
        basedir = os.path.abspath(basedir)

    create_basedir(basedir)
    create_folder_structure(names, basedir)

    # Import GPG key if specified (for encryption)
    if config.get('gpg_import_key') and config.get('gpg_encrypt'):
        print ("\nImporting GPG public key...")
        key_result = import_gpg_key(config['gpg_import_key'])
        if not key_result:
            print ("\nERROR: Failed to import GPG key for account '%s'" % config.get('account_name', 'unknown'))
            print ("ERROR: Cannot proceed with GPG encryption enabled but key import failed")
            print ("ERROR: Aborting backup to prevent unencrypted data from being created")
            server.logout()
            return False

        # If import returned a fingerprint, use it instead of the configured recipient
        if isinstance(key_result, str) and len(key_result) >= 16:
            print ("  Using imported key fingerprint for encryption: %s" % key_result)
            config['gpg_recipient'] = key_result

    # S3 Restore: Download and decrypt files before restore
    if config.get('restore') and config.get('s3_upload'):
        print ("\nDownloading files from S3 for restore...")

        try:
            for foldername, filename in names:
                if foldername in exclude_folders:
                    continue

                # Determine the filename to download (might be encrypted)
                download_filename = filename
                if config.get('gpg_encrypt'):
                    download_filename = filename + '.gpg'

                print ("Downloading: %s" % download_filename)
                try:
                    # Download from S3
                    downloaded_file = download_from_s3(download_filename, config, basedir)

                    # Decrypt if needed
                    if config.get('gpg_encrypt'):
                        print ("Decrypting: %s" % download_filename)
                        try:
                            decrypted_file = decrypt_file_gpg(downloaded_file)
                            # Remove the encrypted file after decryption
                            os.remove(downloaded_file)
                            print ("  Decryption complete")
                        except Exception as e:
                            print ("  ERROR: %s" % str(e))
                            continue

                except Exception as e:
                    print ("  ERROR: %s" % str(e))
                    continue

            print ("\nS3 download complete\n")

        except Exception as e:
            print ("ERROR during S3 download: %s" % str(e))

    # Process each folder
    for name_pair in names:
        try:
            foldername, filename = name_pair
            # Skip excluded folders
            if foldername in exclude_folders:
                print (f'Excluding folder "{foldername}"')
                continue

            if config.get('restore', False):
                # RESTORE MODE: Upload messages from mbox files to IMAP server
                fol_messages = scan_folder(server, foldername, config.get('nospinner', False))
                fil_messages = scan_file(filename, False, config.get('nospinner', False), basedir)

                # Find messages that are in file but not on server
                messages_to_upload = {}
                for msg_id in fil_messages.keys():
                    if msg_id not in fol_messages:
                        messages_to_upload[msg_id] = msg_id

                upload_messages(server, foldername, filename, messages_to_upload,
                              config.get('nospinner', False), basedir)
            else:
                # BACKUP MODE: Download messages from IMAP server to mbox files
                fol_messages = scan_folder(server, foldername, config.get('nospinner', False))
                fil_messages = scan_file(filename, config.get('overwrite', False),
                                       config.get('nospinner', False), basedir)
                new_messages = {}
                for msg_id in fol_messages.keys():
                    if msg_id not in fil_messages:
                        new_messages[msg_id] = fol_messages[msg_id]

                download_messages(server, filename, new_messages, config.get('overwrite', False),
                                config.get('nospinner', False), config.get('thunderbird', False),
                                basedir, config.get('icloud', False))

        except SkipFolderException as e:
            print (e)

    print ("Disconnecting")
    server.logout()

    # S3 Upload: Process and upload mbox files after backup
    if config.get('s3_upload') and not config.get('restore'):
        print ("\nProcessing files for S3 upload...")

        files_to_upload = []
        temp_files_to_cleanup = []
        encryption_failed = False

        try:
            # Collect all mbox files
            for foldername, filename in names:
                if foldername in exclude_folders:
                    continue

                fullname = os.path.join(basedir, filename)
                if os.path.exists(fullname):
                    file_to_upload = fullname

                    # Encrypt if requested
                    if config.get('gpg_encrypt'):
                        print ("Encrypting: %s" % filename)
                        try:
                            encrypted_file = encrypt_file_gpg(fullname, config['gpg_recipient'])
                            file_to_upload = encrypted_file
                            temp_files_to_cleanup.append(encrypted_file)
                        except Exception as e:
                            print ("  ERROR: %s" % str(e))
                            encryption_failed = True
                            continue

                    files_to_upload.append(file_to_upload)

            # Check if any encryption failures occurred
            if encryption_failed and config.get('gpg_encrypt'):
                print ("\n" + "=" * 70)
                print ("ERROR: GPG encryption failed for one or more files")
                print ("ERROR: Cannot upload to S3 with encryption failures")
                print ("ERROR: Aborting to prevent unencrypted data exposure")
                print ("=" * 70)
                return False  # Mark account as failed

            # Upload files to S3
            print ("\nUploading %d file(s) to S3..." % len(files_to_upload))
            for file_path in files_to_upload:
                filename = os.path.basename(file_path)
                print ("Processing: %s" % filename)
                try:
                    upload_to_s3(file_path, config)
                except Exception as e:
                    print ("  ERROR: %s" % str(e))

            print ("\nS3 upload complete")

        finally:
            # Clean up temporary encrypted files
            if temp_files_to_cleanup:
                print ("Cleaning up temporary files...")
                for temp_file in temp_files_to_cleanup:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            print ("  Removed: %s" % os.path.basename(temp_file))
                    except Exception as e:
                        print ("  WARNING: Could not remove %s: %s" % (temp_file, str(e)))

    return True


def main():
    """Main entry point"""
    try:
        config = get_config()

        # Check if using config file mode
        if 'config_file' in config:
            # CONFIG FILE MODE: Process multiple accounts
            print ("Using config file: %s" % config['config_file'])
            print ("")

            # Load config file
            config_data = load_config_file(config['config_file'])
            global_config = config_data.get('global', {})
            accounts = config_data.get('accounts', [])

            if not accounts:
                print ("ERROR: No accounts defined in config file")
                sys.exit(2)

            # Check if list mode was requested
            if config.get('list_backups', False):
                account_filter = config.get('account_filter', [])
                list_backups(global_config, accounts, account_filter)
                sys.exit(0)

            print ("Found %d account(s) to process\n" % len(accounts))

            # Check if restore mode was specified on command line
            restore_mode = config.get('restore', False)

            # Check if account filtering was specified
            account_filter = config.get('account_filter', [])
            if account_filter:
                print ("Account filter active: %s\n" % ', '.join(account_filter))
                # Filter accounts
                accounts = [acc for acc in accounts if acc.get('name') in account_filter]
                if not accounts:
                    print ("ERROR: No accounts matched the filter")
                    sys.exit(2)
                print ("Filtered to %d account(s)\n" % len(accounts))

            # Get date override if specified
            date_override = config.get('date_override')
            if date_override:
                print ("Date override active: %s\n" % date_override)

            # Process each account
            success_count = 0
            failed_count = 0

            for i, account in enumerate(accounts, 1):
                account_name = account.get('name', 'unknown')
                print ("=" * 70)
                print ("Processing account %d/%d: %s" % (i, len(accounts), account_name))
                print ("=" * 70)

                # Parse account config with optional date override
                account_config = parse_account_config(account, global_config, date_override)

                # Override restore mode if specified on command line
                if restore_mode:
                    account_config['restore'] = True

                # Process the account
                success = process_account(account_config)

                if success:
                    success_count += 1
                    print ("\n✓ Account '%s' completed successfully\n" % account_name)
                else:
                    failed_count += 1
                    print ("\n✗ Account '%s' failed\n" % account_name)

            # Summary
            print ("=" * 70)
            print ("Summary: %d successful, %d failed (out of %d total)" %
                   (success_count, failed_count, len(accounts)))
            print ("=" * 70)

            if failed_count > 0:
                sys.exit(1)

        else:
            # COMMAND LINE MODE: Process single account
            if config.get('folders') and config.get('exclude-folders'):
                print("ERROR: You cannot use both --folders and --exclude-folders at the same time")
                sys.exit(2)

            # Use the existing process_account function
            success = process_account(config)

            if not success:
                sys.exit(1)

    except socket.error as e:
        print ("ERROR:", e)
        sys.exit(4)
    except imaplib.IMAP4.error as e:
        print ("ERROR:", e)
        sys.exit(5)


# From http://www.pixelbeat.org/talks/python/spinner.py
def cli_exception(typ, value, traceback):
    """Handle CTRL-C by printing newline instead of ugly stack trace"""
    if not issubclass(typ, KeyboardInterrupt):
        sys.__excepthook__(typ, value, traceback)
    else:
        sys.stdout.write("\n")
        sys.stdout.flush()


if sys.stdin.isatty():
    sys.excepthook = cli_exception


# Hideous fix to counteract http://python.org/sf/1092502
# (which should have been fixed ages ago.)
# Also see http://python.org/sf/1441530
def _fixed_socket_read(self, size=-1):
    data = self._rbuf
    if size < 0:
        # Read until EOF
        buffers = []
        if data:
            buffers.append(data)
        self._rbuf = ""
        if self._rbufsize <= 1:
            recv_size = self.default_bufsize
        else:
            recv_size = self._rbufsize
        while True:
            data = self._sock.recv(recv_size)
            if not data:
                break
            buffers.append(data)
        return "".join(buffers)
    else:
        # Read until size bytes or EOF seen, whichever comes first
        buf_len = len(data)
        if buf_len >= size:
            self._rbuf = data[size:]
            return data[:size]
        buffers = []
        if data:
            buffers.append(data)
        self._rbuf = ""
        while True:
            left = size - buf_len
            recv_size = min(self._rbufsize, left)  # the actual fix
            data = self._sock.recv(recv_size)
            if not data:
                break
            buffers.append(data)
            n = len(data)
            if n >= left:
                self._rbuf = data[left:]
                buffers[-1] = data[:left]
                break
            buf_len += n
        return "".join(buffers)

    
if __name__ == '__main__':
    gc.enable()
    main()
