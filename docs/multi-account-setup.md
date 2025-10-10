---
layout: default
title: Multi-Account Backup Guide - IMAP Backup Tool
description: Complete guide to backing up multiple email accounts with YAML configuration files. Automate backups for Gmail, Office 365, ProtonMail and more.
keywords: multi-account backup, yaml configuration, email backup automation, multiple accounts, batch backup
---

# Multi-Account Backup Configuration

Backup multiple email accounts with a single command using YAML configuration files.

**Auto-detection:** Simply create a `config.yaml` file and run `python3 imapbackup.py` without any arguments. The script automatically detects and uses `config.yaml` or `config.yml` if present in the current directory.

---

## Quick Start

### 1. Install PyYAML

```bash
pip install pyyaml
```

### 2. Create Configuration File

Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

### 3. Edit Your Configuration

```yaml
global:
  basedir: ./backups
  ssl: true
  s3:
    enabled: true
    endpoint: https://s3.hetzner.cloud
    bucket: email-backups
    access_key: YOUR_KEY
    secret_key: YOUR_SECRET
    prefix: backups

accounts:
  - name: personal-gmail
    server: imap.gmail.com
    user: myemail@gmail.com
    pass: my_password

  - name: work-office365
    server: outlook.office365.com
    user: user@company.com
    pass: @/secrets/work_password
```

### 4. Run Backup

```bash
# Automatic detection (looks for config.yaml or config.yml)
python3 imapbackup.py

# Or explicitly specify config file
python3 imapbackup.py --config=config.yaml

# Docker (automatic detection)
docker run --rm -v $(pwd):/data user2k20/imapbackup

# Docker (explicit config)
docker run --rm -v $(pwd):/data user2k20/imapbackup --config=/data/config.yaml
```

**Note:** If you run the script without any arguments and a `config.yaml` or `config.yml` file exists in the current directory, it will automatically be used.

---

## Configuration Structure

### Global Settings

Global settings apply to all accounts unless overridden at the account level.

```yaml
global:
  # Base directory for all backups (each account gets a subdirectory)
  basedir: ./backups

  # Use SSL for all connections
  ssl: true

  # Timeout in seconds
  timeout: 60

  # Disable spinner (useful for logs)
  nospinner: false

  # S3 configuration (optional)
  s3:
    enabled: true
    endpoint: https://s3.eu-central-1.hetzner.cloud
    bucket: email-backups
    access_key: YOUR_S3_ACCESS_KEY
    secret_key: YOUR_S3_SECRET_KEY
    prefix: backups  # Base prefix, account name will be appended

  # GPG encryption (optional)
  gpg:
    enabled: true
    recipient: backup@example.com
    import_key: https://example.com/keys/backup-public.asc
```

### Account Settings

Each account can override global settings and has its own configuration.

```yaml
accounts:
  - name: account-name        # Required: Unique account identifier
    server: imap.gmail.com    # Required: IMAP server hostname
    user: user@example.com    # Required: Email address
    pass: password            # Required: Password (see password options below)
    port: 993                 # Optional: Override default port
    ssl: true                 # Optional: Override global SSL setting
    timeout: 60               # Optional: Override global timeout
    folders: INBOX,Sent       # Optional: Only backup specific folders
    exclude_folders: Trash    # Optional: Exclude specific folders
    s3_prefix: custom/path    # Optional: Custom S3 prefix for this account
    gpg_recipient: other@example.com  # Optional: Account-specific GPG recipient
```

---

## Password Options

Three ways to specify passwords securely:

### 1. Direct Password (Not Recommended for Production)

```yaml
accounts:
  - name: test-account
    server: imap.example.com
    user: user@example.com
    pass: my_password
```

### 2. Password from File (Recommended)

Store password in a separate file with restricted permissions:

```bash
# Create password file
echo "my_secure_password" > ~/.mail_passwords/gmail
chmod 600 ~/.mail_passwords/gmail
```

```yaml
accounts:
  - name: personal-gmail
    server: imap.gmail.com
    user: user@gmail.com
    pass: @/home/user/.mail_passwords/gmail
```

### 3. Password from Environment Variable

```bash
# Set environment variable
export GMAIL_PASSWORD="my_secure_password"
```

```yaml
accounts:
  - name: personal-gmail
    server: imap.gmail.com
    user: user@gmail.com
    pass: env:GMAIL_PASSWORD
```

---

## Directory Structure

### Standard Structure

Each account gets its own subdirectory under the base directory:

```
basedir/
├── personal-gmail/
│   ├── INBOX.mbox
│   ├── Sent.mbox
│   └── Important.mbox
├── work-office365/
│   ├── INBOX.mbox
│   └── Sent.mbox
└── secure-proton/
    ├── INBOX.mbox
    └── Drafts.mbox
```

### Date-Based Structure

Enable `use_date_folders: true` for automatic date organization:

```
basedir/
├── personal-gmail/
│   ├── 2025-10-10/
│   │   ├── INBOX.mbox
│   │   ├── Sent.mbox
│   │   └── Important.mbox
│   ├── 2025-10-11/
│   │   ├── INBOX.mbox
│   │   └── Sent.mbox
│   └── 2025-10-12/
│       └── INBOX.mbox
└── work-office365/
    └── 2025-10-10/
        ├── INBOX.mbox
        └── Sent.mbox
```

**Benefits of date-based folders:**
- Easy to track backup history
- Perfect for daily scheduled backups
- Simple cleanup of old backups
- Clear audit trail

**Configure globally:**
```yaml
global:
  use_date_folders: true
  date_format: '%Y-%m-%d'  # Default: YYYY-MM-DD
```

**Or per-account:**
```yaml
accounts:
  - name: archive-account
    server: imap.example.com
    user: user@example.com
    pass: password
    use_date_folders: true  # Only this account uses dates
    date_format: '%Y-%m-%d'  # Custom format for this account
```

### Date Format Options

Customize the date format using Python strftime patterns:

| Format | Example | Use Case |
|--------|---------|----------|
| `%Y-%m-%d` | 2025-10-10 | Daily backups (default) |
| `%Y/%m/%d` | 2025/10/10 | Hierarchical daily |
| `%Y-%m-%d_%H-%M` | 2025-10-10_14-30 | Hourly backups |
| `%Y/%m` | 2025/10 | Monthly archives |
| `%Y-week-%U` | 2025-week-41 | Weekly backups |
| `%Y/%B/%d` | 2025/October/10 | Human-readable dates |
| `%Y-%m` | 2025-10 | Monthly snapshots |
| `%Y-Q%q` | 2025-Q4 | Quarterly backups |

**Example configurations:**

```yaml
# Daily backups
- name: daily-account
  server: imap.example.com
  user: daily@example.com
  pass: password
  use_date_folders: true
  date_format: '%Y-%m-%d'

# Monthly archives
- name: monthly-account
  server: imap.example.com
  user: monthly@example.com
  pass: password
  use_date_folders: true
  date_format: '%Y/%m'

# Hourly backups
- name: critical-account
  server: imap.example.com
  user: critical@example.com
  pass: password
  use_date_folders: true
  date_format: '%Y-%m-%d_%H-%M'
```

---

## S3 Prefix Structure

### Standard S3 Prefix

S3 prefixes are automatically generated using the account name:

```
{global_prefix}/{account_name}/filename.mbox.gpg

Examples:
backups/personal-gmail/INBOX.mbox.gpg
backups/work-office365/Sent.mbox.gpg
backups/secure-proton/INBOX.mbox.gpg
```

### Date-Based S3 Prefix

When `use_date_folders: true` is enabled:

```
{global_prefix}/{account_name}/{YYYY-MM-DD}/filename.mbox.gpg

Examples:
backups/personal-gmail/2025-10-10/INBOX.mbox.gpg
backups/personal-gmail/2025-10-11/INBOX.mbox.gpg
backups/work-office365/2025-10-10/Sent.mbox.gpg
```

**S3 Lifecycle Benefits:**
- Easy to set retention policies by date
- Automatic expiration of old backups
- Cost optimization with lifecycle rules
- Perfect for compliance requirements

### Custom S3 Prefix

Override the default prefix for specific accounts:

```yaml
accounts:
  - name: personal-gmail
    server: imap.gmail.com
    user: user@gmail.com
    pass: my_password
    s3_prefix: gmail-archive  # Custom prefix instead of "backups/personal-gmail"
```

---

## Account-Specific Overrides

### Override S3 Settings

Use different S3 storage for specific accounts:

```yaml
global:
  s3:
    enabled: true
    endpoint: https://s3.hetzner.cloud
    bucket: general-backups
    access_key: GENERAL_KEY
    secret_key: GENERAL_SECRET

accounts:
  - name: important-account
    server: imap.example.com
    user: user@example.com
    pass: password
    s3:
      bucket: secure-vault  # Override bucket
      prefix: critical      # Override prefix
```

### Disable S3 for Specific Account

```yaml
accounts:
  - name: local-only-account
    server: imap.example.com
    user: user@example.com
    pass: password
    s3_enabled: false  # Disable S3 for this account only
```

### Override GPG Settings

Use different GPG keys for specific accounts:

```yaml
global:
  gpg:
    enabled: true
    recipient: backup@example.com
    import_key: https://example.com/keys/public.asc

accounts:
  - name: secure-account
    server: imap.example.com
    user: user@example.com
    pass: password
    gpg:
      recipient: secure-backup@example.com
      import_key: /path/to/secure-public.asc
```

---

## Folder Filtering

### Backup Only Specific Folders

```yaml
accounts:
  - name: personal-gmail
    server: imap.gmail.com
    user: user@gmail.com
    pass: password
    folders: INBOX,Sent,Important,Work
```

### Exclude Specific Folders

```yaml
accounts:
  - name: work-account
    server: outlook.office365.com
    user: user@company.com
    pass: password
    exclude_folders: Junk Email,Deleted Items,Archive
```

**Note:** You cannot use both `folders` and `exclude_folders` for the same account.

---

## Complete Example

```yaml
# Complete multi-account backup configuration
global:
  basedir: /backups
  ssl: true
  timeout: 120
  nospinner: false

  s3:
    enabled: true
    endpoint: https://s3.eu-central-1.hetzner.cloud
    bucket: email-backups
    access_key: HETZNER_KEY
    secret_key: HETZNER_SECRET
    prefix: backups

  gpg:
    enabled: true
    recipient: backup@example.com
    import_key: env:GPG_PUBLIC_KEY

accounts:
  # Personal Gmail account
  - name: personal-gmail
    server: imap.gmail.com
    port: 993
    user: myemail@gmail.com
    pass: env:GMAIL_PASSWORD
    folders: INBOX,Sent,Important,Projects

  # Work Office 365 account
  - name: work-office365
    server: outlook.office365.com
    user: user@company.com
    pass: @/root/.work_password
    exclude_folders: Junk Email,Deleted Items,Archive

  # ProtonMail account (via Bridge)
  - name: secure-proton
    server: 127.0.0.1
    port: 1143
    user: secure@proton.me
    pass: env:PROTON_PASSWORD
    ssl: false  # ProtonMail Bridge uses local connection
    s3:
      bucket: protonmail-secure
      prefix: encrypted
    gpg:
      recipient: secure-backup@example.com
      import_key: /etc/gpg-keys/secure-public.asc

  # Self-hosted mail server
  - name: personal-selfhosted
    server: mail.example.com
    user: admin@example.com
    pass: @/root/.mail_password
    folders: INBOX,Sent,Drafts
    s3_prefix: selfhosted/admin
```

---

## Running Backups

### Basic Backup

```bash
# Automatic config detection
python3 imapbackup.py

# Or explicitly specify config file
python3 imapbackup.py --config=config.yaml

# Custom config file location
python3 imapbackup.py --config=/path/to/my-config.yaml
```

---

## Listing Available Backups

You can list all available backups (both local and S3) for your accounts:

```bash
# List all backups for all accounts
python3 imapbackup.py --config=config.yaml --list

# List backups for specific account(s)
python3 imapbackup.py --config=config.yaml --list --account=personal-gmail

# List backups for multiple accounts
python3 imapbackup.py --config=config.yaml --list --account=personal-gmail,work-office365
```

**Output example:**
```
Available backups
======================================================================

Account: personal-gmail
----------------------------------------------------------------------
  Local backups:
    Date: 2025-10-10 (15 mbox files)
    Date: 2025-10-09 (15 mbox files)
    Date: 2025-10-08 (14 mbox files)
  S3 backups:
    Date: 2025-10-10 (15 mbox files) in s3://email-backups/backups/personal-gmail/2025-10-10/
    Date: 2025-10-09 (15 mbox files) in s3://email-backups/backups/personal-gmail/2025-10-09/

Account: work-office365
----------------------------------------------------------------------
  Local backups: None found
  S3 backups:
    Date: 2025-10-10 (8 mbox files) in s3://email-backups/backups/work-office365/2025-10-10/
```

The `--list` command shows:
- **Local backups**: Scans the local filesystem for backup directories
- **S3 backups**: Queries S3 storage for backed-up files (if S3 is enabled)
- **Date folders**: Shows available dates for date-based backups
- **File counts**: Number of mbox files in each backup

---

## Selective Account Operations

When you have multiple accounts configured but only want to work with specific ones, use the `--account` flag:

### Backup Specific Accounts

```bash
# Backup only personal-gmail
python3 imapbackup.py --config=config.yaml --account=personal-gmail

# Backup multiple specific accounts
python3 imapbackup.py --config=config.yaml --account=personal-gmail,work-office365
```

### Restore Specific Accounts

```bash
# Restore only one account
python3 imapbackup.py --config=config.yaml --restore --account=personal-gmail

# Restore multiple accounts
python3 imapbackup.py --config=config.yaml --restore --account=personal-gmail,work-office365
```

---

## Selective Date Restore

When using date-based backup folders, you can restore from a specific date using the `--date` flag:

### Restore from a Specific Date

```bash
# Restore personal-gmail from October 9th backup
python3 imapbackup.py --config=config.yaml --restore --account=personal-gmail --date=2025-10-09

# Restore all accounts from October 8th backup
python3 imapbackup.py --config=config.yaml --restore --date=2025-10-08

# Restore specific accounts from specific date
python3 imapbackup.py --config=config.yaml --restore --account=personal-gmail,work-office365 --date=2025-10-09
```

**How it works:**
- The `--date` flag overrides the current date for folder path resolution
- Local path becomes: `./backups/account_name/2025-10-09/`
- S3 prefix becomes: `backups/account_name/2025-10-09/`
- The script will download from S3 (if configured) and restore from that specific date

**Use cases:**
- **Disaster recovery**: Restore from a backup before corruption occurred
- **Point-in-time restore**: Recover emails as they were on a specific date
- **Testing**: Restore to a test environment from a historical backup
- **Compliance**: Restore from archived monthly/weekly backups

---

## Common Scenarios

### Scenario 1: User has 10 accounts but wants to restore only one

```bash
# Step 1: List available backups for the specific account
python3 imapbackup.py --config=config.yaml --list --account=archive-gmail

# Output shows:
#   Date: 2025-10-10 (15 mbox files)
#   Date: 2025-10-09 (15 mbox files)
#   Date: 2025-10-08 (14 mbox files)

# Step 2: Restore from yesterday's backup
python3 imapbackup.py --config=config.yaml --restore --account=archive-gmail --date=2025-10-09
```

### Scenario 2: Selective backup of critical accounts

```bash
# Daily: Backup only critical accounts
python3 imapbackup.py --config=config.yaml --account=critical-account,work-office365

# Weekly: Backup all accounts (no --account flag)
python3 imapbackup.py --config=config.yaml
```

### Scenario 3: Disaster recovery from last week

```bash
# Step 1: Check what backups are available
python3 imapbackup.py --config=config.yaml --list

# Step 2: Restore all accounts from last Friday
python3 imapbackup.py --config=config.yaml --restore --date=2025-10-05
```

### Scenario 4: Monthly archive restore

```bash
# Config uses monthly date format: date_format: '%Y/%m'
# This creates backups like: ./backups/monthly-archive/2025/09/

# Restore September's backup
python3 imapbackup.py --config=config.yaml --restore --account=monthly-archive --date=2025/09
```

---

### Restore Mode

Restore all accounts defined in your config file to their respective IMAP servers:

```bash
# Restore with auto-detected config
python3 imapbackup.py --restore

# Or explicitly specify config file
python3 imapbackup.py --config=config.yaml --restore
```

**How restore works:**
1. Reads the config file to get all account settings
2. For each account:
   - Connects to the IMAP server
   - Downloads from S3 if enabled (and decrypts if GPG is enabled)
   - Compares local mbox files with server folders
   - Uploads only messages that don't already exist on the server
3. Skips duplicate messages automatically

**Use cases:**
- **Email server migration**: Backup from old server, restore to new server
- **Disaster recovery**: Restore from S3 backups to a new mail server
- **Account migration**: Move emails between different email providers
- **Testing**: Restore backups to a test IMAP server

### Docker

```bash
# Automatic config detection (mounts current directory as /data)
docker run --rm \
  -v $(pwd):/data \
  -e GPG_PUBLIC_KEY="$(cat ~/keys/public.asc)" \
  user2k20/imapbackup

# Explicit config file
docker run --rm \
  -v $(pwd)/backups:/backups \
  -v $(pwd)/config.yaml:/config.yaml \
  -e GPG_PUBLIC_KEY="$(cat ~/keys/public.asc)" \
  user2k20/imapbackup \
  --config=/config.yaml
```

### Docker Compose

```yaml
version: '3'
services:
  email-backup:
    image: user2k20/imapbackup:latest
    volumes:
      - ./backups:/backups
      - ./config.yaml:/config.yaml
    environment:
      - GPG_PUBLIC_KEY=${GPG_PUBLIC_KEY}
    command: --config=/config.yaml
```

---

## Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: email-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: user2k20/imapbackup:latest
            args:
              - --config=/config/config.yaml
            volumeMounts:
              - name: config
                mountPath: /config
                readOnly: true
              - name: backups
                mountPath: /backups
            env:
              - name: GPG_PUBLIC_KEY
                valueFrom:
                  secretKeyRef:
                    name: gpg-keys
                    key: public-key
              - name: GMAIL_PASSWORD
                valueFrom:
                  secretKeyRef:
                    name: email-passwords
                    key: gmail
          volumes:
            - name: config
              configMap:
                name: backup-config
            - name: backups
              persistentVolumeClaim:
                claimName: backup-storage
          restartPolicy: OnFailure
```

---

## Automated Backups with Cron

### Daily Backup at 2 AM

```bash
# Edit crontab
crontab -e

# Add entry
0 2 * * * cd /path/to/imapbackup && python3 imapbackup.py --config=config.yaml >> /var/log/email-backup.log 2>&1
```

### Weekly Backup (Sundays at 3 AM)

```bash
0 3 * * 0 cd /path/to/imapbackup && python3 imapbackup.py --config=config.yaml >> /var/log/email-backup.log 2>&1
```

---

## Troubleshooting

### PyYAML Not Found

```bash
# Install PyYAML
pip install pyyaml

# Or use Docker (includes PyYAML)
docker run user2k20/imapbackup --config=/data/config.yaml
```

### Password File Not Found

```bash
# Check file path
ls -la /path/to/password/file

# Verify path in config matches actual file location
# Use absolute paths or relative to script location
```

### Environment Variable Not Set

```bash
# Verify environment variable
echo $GMAIL_PASSWORD

# Export before running
export GMAIL_PASSWORD="my_password"
python3 imapbackup.py --config=config.yaml
```

### Account Subdirectory Not Created

Check that `basedir` in global settings exists and is writable:

```bash
# Create base directory
mkdir -p /path/to/backups
chmod 755 /path/to/backups

# Subdirectories are created automatically
```

---

## Security Best Practices

### 1. Protect Configuration File

```bash
# Set restrictive permissions
chmod 600 config.yaml
```

### 2. Use Password Files

```bash
# Store passwords separately
mkdir -p ~/.mail_passwords
chmod 700 ~/.mail_passwords

# Create password files
echo "password1" > ~/.mail_passwords/gmail
echo "password2" > ~/.mail_passwords/work
chmod 600 ~/.mail_passwords/*
```

### 3. Use Environment Variables

```bash
# Set in secure environment
export GMAIL_PASSWORD="secret"
export WORK_PASSWORD="secret2"

# Run backup
python3 imapbackup.py --config=config.yaml

# Clear variables after
unset GMAIL_PASSWORD WORK_PASSWORD
```

### 4. Enable GPG Encryption

Always encrypt backups when uploading to S3:

```yaml
global:
  gpg:
    enabled: true
    recipient: backup@example.com
    import_key: env:GPG_PUBLIC_KEY
```

---

## Date Format Reference

For complete date format options, see [Python strftime reference](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).

Common format codes:
- `%Y` - 4-digit year (2025)
- `%m` - Month as number (01-12)
- `%d` - Day of month (01-31)
- `%H` - Hour 24-hour (00-23)
- `%M` - Minute (00-59)
- `%B` - Full month name (October)
- `%b` - Abbreviated month (Oct)
- `%U` - Week number (00-53)
- `%A` - Full weekday name (Monday)

---

## See Also

- [Backup Guide](backup-guide.md) - Complete backup strategies
- [S3 Configuration](s3-setup.md) - S3 storage setup
- [GPG Encryption](gpg-setup.md) - Encryption configuration
- [Docker Setup](docker-setup.md) - Docker deployment
