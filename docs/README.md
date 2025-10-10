# IMAP Backup & Restore Documentation

Welcome to the IMAP Backup & Restore tool documentation. This tool allows you to backup, restore, and manage your IMAP email accounts with support for S3 storage and GPG encryption.

## Features

- **Full IMAP Backup**: Download all emails from your IMAP server to local mbox files
- **Smart Restore**: Upload mbox files back to IMAP server (skips duplicates)
- **S3 Integration**: Store backups in S3-compatible storage (MinIO, Hetzner, AWS S3, etc.)
- **GPG Encryption**: Encrypt backups for secure storage
- **Incremental Backups**: Only downloads new messages on subsequent runs
- **Docker Support**: Run easily with Docker using `user2k20/imapbackup` image

## Quick Start

### Using Docker (Recommended)

```bash
# Basic backup
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e

# Backup with S3 upload
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=my-backups \
  --s3-access-key=YOUR_KEY \
  --s3-secret-key=YOUR_SECRET
```

### Using Python Directly

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies
# Ubuntu/Debian:
sudo apt install gnupg

# RHEL/CentOS:
sudo yum install gnupg

# macOS:
brew install gnupg

# Run backup
python3 imapbackup.py \
  -s imap.example.com \
  -u user@example.com \
  -e
```

## Documentation Index

1. **[Docker Setup Guide](docker-setup.md)** - Using the Docker image
2. **[Python/venv Setup Guide](python-setup.md)** - Using Python virtual environments
3. **[Backup Guide](backup-guide.md)** - How to backup your emails
4. **[Restore Guide](restore-guide.md)** - How to restore emails from backups
5. **[S3 Configuration](s3-setup.md)** - Setting up S3 storage (MinIO, Hetzner, AWS)
6. **[GPG Encryption Guide](gpg-setup.md)** - Encrypting your backups
7. **[GPG Key Import Guide](gpg-key-import.md)** - Flexible GPG key import (files, URLs, environment variables)

## Common Use Cases

### Daily Automated Backups

Use cron to schedule daily backups:

```bash
# Run daily at 2 AM
0 2 * * * docker run --rm -v /backups:/data user2k20/imapbackup \
  -s imap.example.com -u user@example.com -p @/root/.imap_password -e
```

### Backup and Upload to S3 with Encryption (Easy Method)

```bash
# Using flexible key import - no GPG keyring mount needed
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=https://example.com/keys/backup-public.asc
```

See [GPG Key Import Guide](gpg-key-import.md) for more examples including environment variables and file paths.

### Backup and Upload to S3 with Encryption (Traditional Method)

```bash
# Using mounted GPG keyring
docker run --rm \
  -v $(pwd)/backups:/data \
  -v $(pwd)/.gnupg:/root/.gnupg \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com
```

### Restore from S3 Encrypted Backup

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  -v $(pwd)/.gnupg:/root/.gnupg \
  user2k20/imapbackup \
  -r \
  -s imap.newserver.com -u user@newserver.com -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com
```

## Command Line Options

### Basic Options

- `-s HOST` - IMAP server hostname
- `-u USER` - Username/email
- `-p PASS` - Password (or `@/path/to/file` to read from file)
- `-e` - Use SSL (recommended)
- `-d DIR` - Directory for mbox files (default: current directory)

### Backup/Restore Modes

- `-a` - Append to existing mbox files (default)
- `-y` - Overwrite existing mbox files
- `-r` - **Restore mode**: Upload mbox files to IMAP server

### Folder Selection

- `-f FOLDERS` - Only backup specific folders (comma-separated)
- `--exclude-folders=FOLDERS` - Exclude specific folders

### S3 Storage Options

- `--s3-upload` - Enable S3 integration
- `--s3-endpoint=URL` - S3 endpoint URL
- `--s3-bucket=BUCKET` - Bucket name
- `--s3-access-key=KEY` - Access key
- `--s3-secret-key=KEY` - Secret key
- `--s3-prefix=PREFIX` - Optional prefix (e.g., `backups/imap/`)

### GPG Encryption Options

- `--gpg-encrypt` - Enable GPG encryption/decryption
- `--gpg-recipient=EMAIL` - GPG key ID or email
- `--gpg-import-key=SOURCE` - Import GPG public key from:
  - File path: `/path/to/key.asc`
  - URL: `https://example.com/key.asc`
  - Environment variable: `env:GPG_PUBLIC_KEY`

## Requirements

### For Docker
- Docker installed
- GPG keyring volume (if using encryption): `-v ~/.gnupg:/root/.gnupg`

### For Python (venv)
- Python 3.6+
- Virtual environment recommended
- Python dependencies: `pip install -r requirements.txt`
- System dependencies:
  - GPG: `apt install gnupg` (Ubuntu/Debian)
  - GPG: `yum install gnupg` (RHEL/CentOS)
  - GPG: `brew install gnupg` (macOS)

## Support

For issues or questions:
- Check the detailed guides in this docs folder
- Review command line options with `--help`
- Check error messages for configuration issues

## Security Notes

1. **Password Storage**: Use `@/path/to/password` to read password from a file
2. **GPG Keys**: Ensure your GPG keyring is properly secured
3. **S3 Credentials**: Use environment variables or secure credential storage
4. **SSL/TLS**: Always use `-e` flag for encrypted IMAP connections

## Next Steps

1. Read the [Docker Setup Guide](docker-setup.md) to get started with Docker
2. Follow the [Backup Guide](backup-guide.md) for your first backup
3. Set up [S3 Storage](s3-setup.md) for cloud backups
4. Configure [GPG Encryption](gpg-setup.md) for secure backups
