---
layout: default
title: Multi-Account Backup Guide - IMAP Backup Tool
description: Complete guide to backing up multiple email accounts with YAML configuration files. Automate backups for Gmail, Office 365, ProtonMail and more.
keywords: multi-account backup, yaml configuration, email backup automation, multiple accounts, batch backup
---

# Multi-Account Backup Configuration

Backup multiple email accounts with a single command using YAML configuration files.

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
# Python
python3 imapbackup.py --config=config.yaml

# Docker
docker run --rm -v $(pwd):/data user2k20/imapbackup --config=/data/config.yaml
```

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

---

## S3 Prefix Structure

S3 prefixes are automatically generated using the account name:

```
{global_prefix}/{account_name}/filename.mbox.gpg

Examples:
backups/personal-gmail/INBOX.mbox.gpg
backups/work-office365/Sent.mbox.gpg
backups/secure-proton/INBOX.mbox.gpg
```

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
python3 imapbackup.py --config=config.yaml
```

### Restore Mode

```bash
python3 imapbackup.py --config=config.yaml --restore
```

### Docker

```bash
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

## See Also

- [Backup Guide](backup-guide.md) - Complete backup strategies
- [S3 Configuration](s3-setup.md) - S3 storage setup
- [GPG Encryption](gpg-setup.md) - Encryption configuration
- [Docker Setup](docker-setup.md) - Docker deployment
