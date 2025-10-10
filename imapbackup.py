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
# - Add proper exception handlers to scanFile() and downloadMessages()
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

    def __init__(self, message, nospinner):
        """Spinner constructor"""
        self.glyphs = "|/-\\"
        self.pos = 0
        self.message = message
        self.nospinner = nospinner
        sys.stdout.write(message)
        sys.stdout.flush()
        self.spin()

    def spin(self):
        """Rotate the spinner"""
        if sys.stdin.isatty() and not self.nospinner:
            sys.stdout.write("\r" + self.message + " " + self.glyphs[self.pos])
            sys.stdout.flush()
            self.pos = (self.pos+1) % len(self.glyphs)

    def stop(self):
        """Erase the spinner from the screen"""
        if sys.stdin.isatty() and not self.nospinner:
            sys.stdout.write("\r" + self.message + "  ")
            sys.stdout.write("\r" + self.message)
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
        True if import succeeded, False otherwise
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
            try:
                # Use subprocess to call curl or wget
                # Try curl first
                try:
                    result = subprocess.run(
                        ['curl', '-fsSL', source],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=30
                    )
                    key_content = result.stdout
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fall back to wget
                    result = subprocess.run(
                        ['wget', '-qO-', source],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=30
                    )
                    key_content = result.stdout

                if not key_content or len(key_content) < 100:
                    raise Exception("Downloaded key appears to be empty or invalid")
                source_description = "URL %s" % source
            except subprocess.TimeoutExpired:
                raise Exception("Timeout while downloading key from %s" % source)
            except Exception as e:
                raise Exception("Failed to download key from URL: %s" % str(e))

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
            cmd = ['gpg', '--batch', '--import', temp_key_file]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            print("  Successfully imported GPG key from %s" % source_description)

            # Show imported key info if available in stderr
            if result.stderr:
                # GPG outputs import info to stderr
                for line in result.stderr.split('\n'):
                    if 'imported:' in line.lower() or 'public key' in line.lower():
                        print("  %s" % line.strip())

            return True

        finally:
            # Clean up temp file
            if os.path.exists(temp_key_file):
                os.unlink(temp_key_file)

    except Exception as e:
        print("  WARNING: Failed to import GPG key: %s" % str(e))
        return False


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
    """Download a file from S3-compatible storage using AWS CLI"""
    try:
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

        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

        print ("  Download complete")
        return destination_path

    except subprocess.CalledProcessError as e:
        raise Exception("S3 download failed: %s\n%s" % (e.stderr, e.stdout))


def upload_to_s3(file_path, config):
    """Upload a file to S3-compatible storage using AWS CLI"""
    try:
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

        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

        print ("  Upload complete")
        return True

    except subprocess.CalledProcessError as e:
        raise Exception("S3 upload failed: %s\n%s" % (e.stderr, e.stdout))


def upload_messages(server, foldername, filename, messages_to_upload, nospinner, basedir):
    """Upload messages from mbox file to IMAP folder"""

    fullname = os.path.join(basedir, filename)

    # Check if file exists
    if not os.path.exists(fullname):
        print ("File %s: not found, skipping" % filename)
        return

    # nothing to do
    if not len(messages_to_upload):
        print ("Messages to upload: 0")
        return

    spinner = Spinner("Uploading %s messages to %s" % (len(messages_to_upload), foldername),
                      nospinner)

    # Open the mbox file
    mbox = mailbox.mbox(fullname)

    uploaded = 0
    total_size = 0

    # Iterate through messages in the mbox file
    for message in mbox:
        # Get the Message-Id
        msg_id = message.get('Message-Id', '').strip()

        # Check if this message needs to be uploaded
        if msg_id in messages_to_upload:
            # Convert message to string (bytes)
            msg_bytes = bytes(str(message), 'utf-8')

            # Upload to IMAP server
            # Use APPEND command to add message to folder
            try:
                # Select the folder for append (need to ensure it exists)
                foldername_quoted = '"{}"'.format(foldername)

                # APPEND the message
                result = server.append(foldername_quoted, None, None, msg_bytes)

                if result[0] == 'OK':
                    uploaded += 1
                    total_size += len(msg_bytes)
                else:
                    print ("\nWarning: Failed to upload message with ID: %s" % msg_id)

            except Exception as e:
                print ("\nError uploading message %s: %s" % (msg_id, str(e)))

            spinner.spin()

    mbox.close()
    spinner.stop()
    print (": %s uploaded, %s total" % (uploaded, pretty_byte_count(total_size)))


def download_messages(server, filename, messages, overwrite, nospinner, thunderbird, basedir, icloud):
    """Download messages from folder and append to mailbox"""

    fullname = os.path.join(basedir,filename)

    if overwrite and os.path.exists(fullname):
        print ("Deleting mbox: {0} at: {1}".format(filename,fullname))
        os.remove(fullname)
    
    # Open disk file for append in binary mode
    mbox = open(fullname, 'ab')

    # the folder has already been selected by scanFolder()

    # nothing to do
    if not len(messages):
        print ("New messages: 0")
        mbox.close()
        return

    spinner = Spinner("Downloading %s new messages to %s" % (len(messages), filename),
                      nospinner)
    total = biggest = 0
    from_re = re.compile(b"\n(>*)From ")

    # each new message
    for msg_id in messages.keys():

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

        # fetch message
        msg_id_str = str(messages[msg_id])
        typ, data = server.fetch(msg_id_str, "(BODY.PEEK[])" if icloud else "(RFC822)")


        assert('OK' == typ)
        data_bytes = data[0][1]

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
        mbox.write(text_bytes)
        mbox.write(b'\n\n')

        size = len(text_bytes)
        biggest = max(size, biggest)
        total += size

        del data
        gc.collect()
        spinner.spin()

    mbox.close()
    spinner.stop()
    print (": %s total, %s for largest message" % (pretty_byte_count(total),
                                                  pretty_byte_count(biggest)))


def scan_file(filename, overwrite, nospinner, basedir):
    """Gets IDs of messages in the specified mbox file"""
    # file will be overwritten
    if overwrite:
        return []
    
    fullname = os.path.join(basedir,filename)

    # file doesn't exist
    if not os.path.exists(fullname):
        print ("File %s: not found" % filename)
        return []

    spinner = Spinner("File %s" % filename, nospinner)

    # open the mailbox file for read
    mbox = mailbox.mbox(fullname)

    messages = {}

    # each message
    i = 0
    HEADER_MESSAGE_ID='Message-Id'
    for message in mbox:
        header = ''
        # We assume all messages on disk have message-ids
        try:
            header = "{0}: {1}".format(HEADER_MESSAGE_ID,message.get(HEADER_MESSAGE_ID))
        except KeyError:
            # No message ID was found. Warn the user and move on
            print
            print ("WARNING: Message #%d in %s" % (i, filename),)
            print ("has no {0} header.".format(HEADER_MESSAGE_ID))

        header = BLANKS_RE.sub(' ', header.strip())
        try:
            msg_id = MSGID_RE.match(header).group(1)
            if msg_id not in messages.keys():
                # avoid adding dupes
                messages[msg_id] = msg_id
        except AttributeError:
            # Message-Id was found but could somehow not be parsed by regexp
            # (highly bloody unlikely)
            print
            print ("WARNING: Message #%d in %s" % (i, filename),)
            print ("has a malformed {0} header.".format(HEADER_MESSAGE_ID))
        spinner.spin()
        i = i + 1

    # done
    mbox.close()
    spinner.stop()
    print (": %d messages" % (len(messages.keys())))
    return messages


def scan_folder(server, foldername, nospinner):
    """Gets IDs of messages in the specified folder, returns id:num dict"""
    messages = {}
    foldername = '"{}"'.format(foldername)
    spinner = Spinner("Folder %s" % foldername, nospinner)
    try:
        typ, data = server.select(foldername, readonly=True)
        if 'OK' != typ:
            raise SkipFolderException("SELECT failed: %s" % data)
        num_msgs = int(data[0])

        # Retrieve all Message-Id headers, making sure we don't mark all messages as read.
        #
        # The result is an array of result tuples with a terminating closing parenthesis
        # after each tuple. That means that the first result is at index 0, the second at
        # 2, third at 4, and so on.
        #
        # e.g.
        # [
        #   (b'1 (BODY[...', b'Message-Id: ...'), b')', # indices 0 and 1
        #   (b'2 (BODY[...', b'Message-Id: ...'), b')', # indices 2 and 3
        #   ...
        #  ]
        if num_msgs > 0:
            typ, data = server.fetch(f'1:{num_msgs}', '(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])')
            if 'OK' != typ:
                raise SkipFolderException("FETCH failed: %s" % (data))

        # each message
        for i in range(0, num_msgs):
            num = 1 + i

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
                msg_typ, msg_data = server.fetch(
                    str(num), '(BODY[HEADER.FIELDS (FROM TO CC DATE SUBJECT)])')
                if 'OK' != msg_typ:
                    raise SkipFolderException(
                        "FETCH %s failed: %s" % (num, msg_data))
                data_str = str(msg_data[0][1], 'utf-8', 'replace')
                header = data_str.strip()
                header = header.replace('\r\n', '\t').encode('utf-8')
                messages['<' + UUID + '.' +
                         hashlib.sha1(header).hexdigest() + '>'] = num
            spinner.spin()
    finally:
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


def parse_account_config(account, global_config):
    """Parse a single account configuration, merging with global settings"""
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

        # S3 prefix: use custom or build from global prefix + account name
        if 's3_prefix' in account:
            config['s3_prefix'] = account['s3_prefix']
        elif 's3_prefix' in account_s3:
            config['s3_prefix'] = account_s3['prefix']
        else:
            global_prefix = global_s3.get('prefix', 'backups')
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
    print ("")
    print ("Config File Mode:")
    print (" --config=FILE                 Load settings from YAML config file.")
    print ("                               Allows backing up multiple accounts.")
    print ("                               See config.example.yaml for format.")
    print (" --restore                     Restore mode (use with --config).")
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
                     "s3-prefix=", "gpg-encrypt", "gpg-recipient=", "gpg-import-key=", "config="]
        opts, extraargs = getopt.getopt(sys.argv[1:], short_args, long_args)
    except getopt.GetoptError:
        print_usage()

    warnings = []
    config = {'overwrite': False, 'usessl': False,
              'thunderbird': False, 'nospinner': False,
              'basedir': ".", 'icloud': False, 'restore': False,
              's3_upload': False, 'gpg_encrypt': False}
    errors = []

    # empty command line
    if not len(opts) and not len(extraargs):
        print_usage()

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
    config, warnings, errors = check_config(config, warnings, errors)

    # show warnings
    for warning in warnings:
        print ("WARNING:", warning)

    # show errors, exit
    for error in errors:
        print ("ERROR", error)
    if len(errors):
        sys.exit(2)

    # prompt for password, if necessary
    if 'pass' not in config:
        config['pass'] = getpass.getpass()

    # defaults
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
    """Connects to the server and logs in.  Returns IMAP4 object."""
    try:
        assert(not (('keyfilename' in config) ^ ('certfilename' in config)))
        if config['timeout']:
            socket.setdefaulttimeout(config['timeout'])

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
            print ("ERROR: could not connect to '%s' (%s)" % (
                config['server'], e))

        sys.exit(4)

    return server



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
        import_gpg_key(config['gpg_import_key'])

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
                            continue

                    files_to_upload.append(file_to_upload)

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

            print ("Found %d account(s) to process\n" % len(accounts))

            # Check if restore mode was specified on command line
            restore_mode = config.get('restore', False)

            # Process each account
            success_count = 0
            failed_count = 0

            for i, account in enumerate(accounts, 1):
                account_name = account.get('name', 'unknown')
                print ("=" * 70)
                print ("Processing account %d/%d: %s" % (i, len(accounts), account_name))
                print ("=" * 70)

                # Parse account config
                account_config = parse_account_config(account, global_config)

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
