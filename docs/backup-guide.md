# Backup Guide

Complete guide for backing up your IMAP emails using the imapbackup tool.

## Table of Contents

- [Basic Backups](#basic-backups)
- [Incremental Backups](#incremental-backups)
- [Selective Backups](#selective-backups)
- [Cloud Backups](#cloud-backups)
- [Encrypted Backups](#encrypted-backups)
- [Best Practices](#best-practices)

## Basic Backups

### First Time Backup

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e
```

This will:
1. Connect to your IMAP server via SSL
2. Prompt for your password
3. Download all folders and messages
4. Save them as mbox files in `./backups/`

### With Password File

```bash
# Create password file
echo "your_password" > .imap_password
chmod 600 .imap_password

# Run backup
docker run --rm \
  -v $(pwd)/backups:/data \
  -v $(pwd)/.imap_password:/secrets/password:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p @/secrets/password \
  -e
```

### Specify Backup Directory

```bash
docker run --rm \
  -v /mnt/storage/email-backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -d /data
```

## Incremental Backups

By default, the tool performs incremental backups - only new messages are downloaded on subsequent runs.

### Append Mode (Default)

```bash
# First run - downloads everything
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup -s imap.example.com -u user@example.com -e

# Second run - only downloads new messages
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup -s imap.example.com -u user@example.com -e
```

### Force Full Backup (Overwrite)

Use `-y` to overwrite existing backups:

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -y
```

## Selective Backups

### Backup Specific Folders

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -f "INBOX,Sent,Important,Work"
```

### Exclude Specific Folders

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --exclude-folders="Trash,Spam,Junk"
```

### Backup Only INBOX

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -f "INBOX"
```

## Cloud Backups

### Backup to MinIO

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://play.min.io:9000 \
  --s3-bucket=email-backups \
  --s3-access-key=minioadmin \
  --s3-secret-key=minioadmin \
  --s3-prefix=user@example.com/
```

### Backup to Hetzner S3

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.hetzner.cloud \
  --s3-bucket=my-email-backups \
  --s3-access-key=$HETZNER_ACCESS_KEY \
  --s3-secret-key=$HETZNER_SECRET_KEY \
  --s3-prefix=backups/$(date +%Y-%m)/
```

### Backup to AWS S3

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.us-east-1.amazonaws.com \
  --s3-bucket=my-backups \
  --s3-access-key=$AWS_ACCESS_KEY_ID \
  --s3-secret-key=$AWS_SECRET_ACCESS_KEY \
  --s3-prefix=email-backups/
```

## Encrypted Backups

### Backup with GPG Encryption

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=secure-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com
```

This will:
1. Download emails to local mbox files
2. Encrypt each mbox file with GPG
3. Upload encrypted files to S3
4. Delete temporary encrypted files from local disk
5. Keep unencrypted local mbox files

### Encrypted Backup Without Local Copy

To remove local files after S3 upload:

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=secure-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  && rm /data/*.mbox
```

## Backup Strategies

### Daily Incremental Backups

Create a script for daily backups:

```bash
#!/bin/bash
# daily-backup.sh

BACKUP_DIR="/mnt/backups/email"
LOG_FILE="/var/log/email-backup.log"

echo "Starting backup at $(date)" >> "$LOG_FILE"

docker run --rm \
  -v $BACKUP_DIR:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p @/root/.imap_password \
  -e \
  --nospinner >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "Backup completed successfully at $(date)" >> "$LOG_FILE"
else
    echo "Backup failed at $(date)" >> "$LOG_FILE"
    exit 1
fi
```

### Weekly Full Backup with S3

```bash
#!/bin/bash
# weekly-full-backup.sh

WEEK=$(date +%Y-W%U)
S3_PREFIX="weekly-backups/$WEEK/"

docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p @/root/.imap_password \
  -e \
  -y \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --s3-prefix="$S3_PREFIX"
```

### Monthly Encrypted Archive

```bash
#!/bin/bash
# monthly-archive.sh

MONTH=$(date +%Y-%m)
S3_PREFIX="monthly-archives/$MONTH/"

docker run --rm \
  -v $(pwd)/temp-backup:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p @/root/.imap_password \
  -e \
  -y \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=email-archives \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --s3-prefix="$S3_PREFIX" \
  --gpg-encrypt \
  --gpg-recipient=archive@example.com

# Clean up local temp files
rm -rf $(pwd)/temp-backup/*
```

## Best Practices

### 1. Test Your Backups

Always verify that backups are working:

```bash
# List files in backup
ls -lh backups/

# Check a specific mbox file
file backups/INBOX.mbox

# Count messages
grep -c "^From " backups/INBOX.mbox
```

### 2. Monitor Backup Size

```bash
# Check backup directory size
du -sh backups/

# Check S3 bucket usage
aws s3 ls s3://your-bucket --recursive --summarize
```

### 3. Keep Multiple Backup Locations

- Local disk backups (fast access)
- S3 cloud storage (offsite)
- Encrypted archives (long-term)

### 4. Rotation Policy

Example: Keep daily backups for 7 days, weekly for 4 weeks, monthly for 12 months

```bash
#!/bin/bash
# backup-rotation.sh

# Daily backup
if [ $(date +%d) == "01" ]; then
    # Monthly backup on the 1st
    DEST="monthly/$(date +%Y-%m)"
else
    # Daily backup
    DEST="daily/$(date +%Y-%m-%d)"
fi

docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=backups \
  --s3-prefix="$DEST/" \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET

# Clean up old daily backups (keep 7 days)
find backups/daily -type f -mtime +7 -delete

# Clean up old monthly backups (keep 12 months)
find backups/monthly -type f -mtime +365 -delete
```

### 5. Verify Encryption

After encrypted backup, verify files are encrypted:

```bash
# Try to read encrypted file - should see binary data
head backups/INBOX.mbox.gpg

# Verify GPG encryption
gpg --list-packets backups/INBOX.mbox.gpg
```

### 6. Document Your Setup

Keep a record of:
- IMAP server settings
- Backup schedule
- S3 configuration
- GPG key IDs
- Restore procedures

## Troubleshooting

### Backup Takes Too Long

- Use `-f` to backup specific folders only
- Increase network timeout with `-t 300`
- Check network connectivity

### Out of Disk Space

```bash
# Check available space
df -h

# Compress old backups
gzip backups/*.mbox

# Move to S3 and delete local
docker run --rm -v $(pwd)/backups:/data user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e \
  --s3-upload --s3-endpoint=... --s3-bucket=...
rm backups/*.mbox
```

### Connection Errors

- Verify IMAP server and port
- Check SSL/TLS requirements
- Test credentials manually
- Check firewall/proxy settings

## Next Steps

- [Restore Guide](restore-guide.md) - Learn how to restore backups
- [S3 Setup](s3-setup.md) - Configure S3 providers
- [GPG Setup](gpg-setup.md) - Set up encryption keys
