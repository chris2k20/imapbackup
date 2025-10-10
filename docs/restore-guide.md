# Restore Guide

Complete guide for restoring emails from backups to your IMAP server.

## Table of Contents

- [Understanding Restore Mode](#understanding-restore-mode)
- [Basic Restore](#basic-restore)
- [Restore from S3](#restore-from-s3)
- [Restore Encrypted Backups](#restore-encrypted-backups)
- [Migration Scenarios](#migration-scenarios)
- [Troubleshooting](#troubleshooting)

## Understanding Restore Mode

The restore mode (`-r` flag) uploads messages from local mbox files to your IMAP server. Key features:

- **Smart Duplicate Detection**: Only uploads messages that don't already exist on the server (based on Message-ID)
- **Folder Preservation**: Maintains original folder structure
- **S3 Integration**: Can download backups from S3 before restoring
- **GPG Decryption**: Automatically decrypts encrypted backups from S3

## Basic Restore

### Restore from Local Backups

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e
```

This will:
1. Connect to the IMAP server
2. Read mbox files from `/data`
3. Upload messages that don't exist on the server
4. Skip messages that are already present

### Restore Specific Folders

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -f "INBOX,Sent,Important"
```

### Restore to Different Server

```bash
# Restore from old server backup to new server
docker run --rm \
  -v $(pwd)/old-server-backup:/data \
  user2k20/imapbackup \
  -r \
  -s imap.newserver.com \
  -u user@newserver.com \
  -e
```

## Restore from S3

### Basic S3 Restore

```bash
docker run --rm \
  -v $(pwd)/temp-restore:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET
```

The tool will:
1. Download all mbox files from S3 to `/data`
2. Restore them to the IMAP server
3. Leave local copies in `/data` (clean up manually if needed)

### Restore from S3 with Prefix

```bash
docker run --rm \
  -v $(pwd)/restore:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --s3-prefix=backups/2025-01/
```

## Restore Encrypted Backups

### Restore from S3 with GPG Decryption

```bash
docker run --rm \
  -v $(pwd)/restore:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=encrypted-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com
```

The tool will:
1. Download `.gpg` files from S3
2. Decrypt them using your GPG private key
3. Restore decrypted mbox files to IMAP
4. Clean up encrypted files (keeps decrypted mbox files)

**Note**: You must have the GPG private key that can decrypt these files in your keyring.

### Decrypt Local Backup

If you have encrypted files locally:

```bash
# Manual decryption first
gpg --decrypt-files backups/*.gpg

# Then restore
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e
```

## Migration Scenarios

### Migrate Between Email Providers

```bash
#!/bin/bash
# migrate-email.sh

# Step 1: Backup from old provider
docker run --rm \
  -v $(pwd)/migration:/data \
  user2k20/imapbackup \
  -s old-imap.provider.com \
  -u user@oldprovider.com \
  -e

# Step 2: Restore to new provider
docker run --rm \
  -v $(pwd)/migration:/data \
  user2k20/imapbackup \
  -r \
  -s new-imap.provider.com \
  -u user@newprovider.com \
  -e
```

### Migrate from Self-Hosted to Cloud

```bash
# Backup from self-hosted
docker run --rm \
  -v $(pwd)/migration:/data \
  user2k20/imapbackup \
  -s mail.mydomain.com \
  -u user@mydomain.com \
  -e

# Restore to Gmail/Google Workspace
docker run --rm \
  -v $(pwd)/migration:/data \
  user2k20/imapbackup \
  -r \
  -s imap.gmail.com \
  -u user@mydomain.com \
  -e
```

### Disaster Recovery from S3

```bash
#!/bin/bash
# disaster-recovery.sh

echo "Starting disaster recovery..."

# Download and restore from S3
docker run --rm \
  -v $(pwd)/recovery:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -p @/root/.imap_password \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=disaster-recovery \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=recovery@example.com

echo "Disaster recovery completed!"
```

### Merge Multiple Accounts

```bash
#!/bin/bash
# merge-accounts.sh

# Backup Account 1
docker run --rm \
  -v $(pwd)/account1:/data \
  user2k20/imapbackup \
  -s imap.provider.com \
  -u user1@example.com \
  -e

# Backup Account 2
docker run --rm \
  -v $(pwd)/account2:/data \
  user2k20/imapbackup \
  -s imap.provider.com \
  -u user2@example.com \
  -e

# Merge locally (copy files)
cp account2/*.mbox account1/

# Restore all to new account
docker run --rm \
  -v $(pwd)/account1:/data \
  user2k20/imapbackup \
  -r \
  -s imap.provider.com \
  -u merged@example.com \
  -e
```

## Selective Restore

### Restore Only INBOX

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -f "INBOX"
```

### Restore Excluding Trash

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --exclude-folders="Trash,Spam,Junk"
```

## Verification

### Verify Restore Completion

```bash
# Before restore - count messages in backup
grep -c "^From " backups/INBOX.mbox

# After restore - check IMAP server
# (Use IMAP client or webmail to verify)
```

### Test Restore with Limited Folder

```bash
# Test with a single folder first
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap-test.example.com \
  -u test@example.com \
  -e \
  -f "INBOX" \
  --nospinner
```

## Best Practices

### 1. Test on Non-Production Account First

```bash
# Create a test account and restore there first
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u test-restore@example.com \
  -e
```

### 2. Backup Before Restore

If restoring to an existing account with data:

```bash
# Backup existing data first
docker run --rm \
  -v $(pwd)/current-backup:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e

# Then perform restore
docker run --rm \
  -v $(pwd)/restore-backup:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e
```

### 3. Monitor Progress

Use `--nospinner` for better logging:

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --nospinner | tee restore.log
```

### 4. Clean Up After S3 Restore

```bash
# Restore from S3
docker run --rm \
  -v $(pwd)/temp-restore:/data \
  user2k20/imapbackup \
  -r -s imap.example.com -u user@example.com -e \
  --s3-upload --s3-endpoint=... --s3-bucket=...

# Clean up downloaded files
rm -rf $(pwd)/temp-restore/*
```

### 5. Document the Process

Keep a restore runbook with:
- S3 bucket and prefix locations
- GPG key information
- IMAP server settings
- Folder mappings
- Testing procedures

## Troubleshooting

### "File not found" Errors

```bash
# List available mbox files
ls -lh backups/

# Ensure volume mount is correct
docker run --rm -v $(pwd)/backups:/data alpine ls -lh /data
```

### GPG Decryption Fails

```bash
# Verify GPG key is available
gpg --list-secret-keys

# Test decryption manually
gpg --decrypt backups/INBOX.mbox.gpg > test.mbox

# Check GPG volume mount
docker run --rm -v ~/.gnupg:/root/.gnupg:ro alpine ls -la /root/.gnupg
```

### S3 Download Fails

```bash
# Test S3 credentials
docker run --rm amazon/aws-cli \
  s3 ls s3://your-bucket \
  --endpoint-url=https://s3.hetzner.cloud

# Check network connectivity
ping s3.hetzner.cloud

# Verify S3 bucket and prefix
aws s3 ls s3://your-bucket/prefix/ --endpoint-url=...
```

### Duplicate Messages

The tool automatically skips duplicates based on Message-ID. If you see "Messages to upload: 0", it means all messages already exist on the server.

### Connection Timeouts

Increase timeout for slow connections:

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -t 300
```

### Folder Structure Issues

Some IMAP servers use different folder delimiters. The tool handles this automatically, but verify folders were created correctly after restore.

## Post-Restore Checklist

- [ ] Verify all folders were restored
- [ ] Check message counts match backup
- [ ] Test searching for specific emails
- [ ] Verify attachments are intact
- [ ] Check folder hierarchy is correct
- [ ] Test email client connectivity
- [ ] Clean up temporary files
- [ ] Document what was restored
- [ ] Update backup schedule if needed

## Next Steps

- [Backup Guide](backup-guide.md) - Set up ongoing backups
- [S3 Setup](s3-setup.md) - Configure S3 storage
- [GPG Setup](gpg-setup.md) - Manage encryption keys
