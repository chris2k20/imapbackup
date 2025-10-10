---
layout: default
title: GPG Encryption Setup Guide - Secure Email Backups
description: Complete guide for setting up GPG encryption for secure IMAP email backups. Learn how to create keys, encrypt backups, and manage GPG in Docker.
keywords: gpg encryption, email encryption, pgp backup, encrypted email backup, gpg docker, openpgp backup, secure email storage
---

# GPG Encryption Setup Guide

Complete guide for setting up GPG encryption for secure email backups.

> **💡 New Feature**: For Docker users, check out the [GPG Key Import Guide](gpg-key-import.md) for a simpler way to use GPG encryption without mounting keyrings. You can now import public keys from files, URLs, or environment variables using `--gpg-import-key`.

## Table of Contents

- [Why Use GPG Encryption](#why-use-gpg-encryption)
- [Installing GPG](#installing-gpg)
- [Creating GPG Keys](#creating-gpg-keys)
- [Exporting and Backing Up Keys](#exporting-and-backing-up-keys)
- [Using GPG with Docker](#using-gpg-with-docker)
- [Key Management](#key-management)
- [Best Practices](#best-practices)

## Why Use GPG Encryption

GPG (GNU Privacy Guard) encryption provides:

- **End-to-end encryption**: Files are encrypted before upload to S3
- **Security**: Only holders of the private key can decrypt
- **Compliance**: Meets data protection requirements (GDPR, HIPAA)
- **Trust**: Industry-standard encryption (OpenPGP)

### Use Cases

- Storing backups in untrusted locations
- Multi-tenant backup systems
- Regulatory compliance requirements
- Long-term archival with security guarantees

## Installing GPG

### On Linux

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install gnupg

# RHEL/CentOS/Fedora
sudo yum install gnupg

# Arch Linux
sudo pacman -S gnupg
```

### On macOS

```bash
# Using Homebrew
brew install gnupg
```

### On Windows

Download from [GnuPG website](https://gnupg.org/download/) or use [Gpg4win](https://www.gpg4win.org/)

### Verify Installation

```bash
gpg --version
```

## Creating GPG Keys

### Generate a New Key Pair

```bash
gpg --full-generate-key
```

Follow the prompts:

1. **Key type**: Select `(1) RSA and RSA (default)`
2. **Key size**: Choose `4096` for maximum security
3. **Expiration**: Recommend `0` (never expire) for backup keys
4. **Real name**: Your name or `Email Backup Key`
5. **Email**: `backup@example.com` or your email
6. **Comment**: `Email backup encryption key`
7. **Passphrase**: **Important**: Set a strong passphrase

Example:
```bash
$ gpg --full-generate-key
gpg (GnuPG) 2.2.19; Copyright (C) 2019 Free Software Foundation, Inc.

Please select what kind of key you want:
   (1) RSA and RSA (default)
   (2) DSA and Elgamal
   (3) DSA (sign only)
   (4) RSA (sign only)
Your selection? 1

RSA keys may be between 1024 and 4096 bits long.
What keysize do you want? (3072) 4096

Please specify how long the key should be valid.
         0 = key does not expire
      <n>  = key expires in n days
      <n>w = key expires in n weeks
      <n>m = key expires in n months
      <n>y = key expires in n years
Key is valid for? (0) 0

Real name: Email Backup
Email address: backup@example.com
Comment: Backup encryption key
You selected this USER-ID:
    "Email Backup (Backup encryption key) <backup@example.com>"

Change (N)ame, (C)omment, (E)mail or (O)kay/(Q)uit? O
```

### Quick Generation for Testing

```bash
# Fast key generation for testing (NOT for production)
gpg --batch --generate-key <<EOF
Key-Type: RSA
Key-Length: 2048
Name-Real: Test Backup
Name-Email: test@example.com
Expire-Date: 0
%no-protection
EOF
```

### List Your Keys

```bash
# List public keys
gpg --list-keys

# List private keys
gpg --list-secret-keys
```

## Exporting and Backing Up Keys

### Export Public Key

```bash
# Export to file
gpg --export --armor backup@example.com > backup-public-key.asc

# Display key
gpg --export --armor backup@example.com
```

### Export Private Key

**⚠️ IMPORTANT**: Keep your private key secure!

```bash
# Export private key
gpg --export-secret-keys --armor backup@example.com > backup-private-key.asc

# Secure the file
chmod 600 backup-private-key.asc
```

### Backup Your Keys

```bash
#!/bin/bash
# backup-gpg-keys.sh

BACKUP_DIR="$HOME/secure-backup"
KEY_EMAIL="backup@example.com"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Export public key
gpg --export --armor "$KEY_EMAIL" > "$BACKUP_DIR/public-$DATE.asc"

# Export private key
gpg --export-secret-keys --armor "$KEY_EMAIL" > "$BACKUP_DIR/private-$DATE.asc"

# Export trust database
gpg --export-ownertrust > "$BACKUP_DIR/ownertrust-$DATE.txt"

# Secure the directory
chmod 700 "$BACKUP_DIR"
chmod 600 "$BACKUP_DIR"/*

echo "GPG keys backed up to $BACKUP_DIR"

# Optional: Encrypt the backup
tar czf - "$BACKUP_DIR" | gpg --encrypt --recipient "$KEY_EMAIL" > gpg-backup-$DATE.tar.gz.gpg
```

### Import Keys on Another System

```bash
# Import public key
gpg --import backup-public-key.asc

# Import private key
gpg --import backup-private-key.asc

# Import trust
gpg --import-ownertrust < ownertrust.txt

# Verify
gpg --list-secret-keys
```

## Using GPG with Docker

### Method 1: Flexible Key Import (Recommended)

**No keyring mount needed** - Import public keys from files, URLs, or environment variables:

```bash
# From URL (great for automation)
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=encrypted-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=https://example.com/keys/backup-public.asc

# From environment variable
export GPG_PUBLIC_KEY=$(cat ~/keys/backup-public.asc)
docker run --rm \
  -v $(pwd)/backups:/data \
  -e GPG_PUBLIC_KEY \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=env:GPG_PUBLIC_KEY

# From file in Docker image
docker run --rm \
  -v $(pwd)/backups:/data \
  -v $(pwd)/backup-public.asc:/etc/gpg-key.asc:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=/etc/gpg-key.asc
```

**Benefits**:
- No GPG keyring management
- Public keys are safe to distribute
- Perfect for containers and automation
- Works with Kubernetes ConfigMaps

See the [GPG Key Import Guide](gpg-key-import.md) for complete examples and workflows.

### Method 2: Share GPG Keyring with Container (Traditional)

Mount your GPG directory (useful when you have existing keyrings):

```bash
# Mount GPG directory (read-only recommended)
docker run --rm \
  -v $(pwd)/backups:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
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

**Note**: This method requires managing GPG permissions and is needed for **restore/decryption** (which requires the private key).

### Fix GPG Permissions

```bash
# GPG requires specific permissions
chmod 700 ~/.gnupg
chmod 600 ~/.gnupg/*
chmod 700 ~/.gnupg/*.d
```

### Test GPG in Docker

```bash
# Test that GPG can access your keys
docker run --rm \
  -v ~/.gnupg:/root/.gnupg:ro \
  alpine:latest sh -c "apk add gnupg && gpg --list-keys"
```

## Encryption and Decryption Examples

### Encrypt a File

```bash
# Encrypt for specific recipient
gpg --encrypt --recipient backup@example.com file.txt

# Encrypt with armor (ASCII output)
gpg --encrypt --armor --recipient backup@example.com file.txt

# Encrypt for multiple recipients
gpg --encrypt \
  --recipient backup@example.com \
  --recipient recovery@example.com \
  file.txt
```

### Decrypt a File

```bash
# Decrypt file
gpg --decrypt file.txt.gpg > file.txt

# Decrypt to specific output
gpg --output file.txt --decrypt file.txt.gpg

# Batch mode (no prompts)
gpg --batch --yes --decrypt file.txt.gpg > file.txt
```

### Test Encryption/Decryption

```bash
# Create test file
echo "Test backup data" > test.txt

# Encrypt
gpg --encrypt --recipient backup@example.com test.txt

# Verify encrypted
file test.txt.gpg

# Decrypt
gpg --decrypt test.txt.gpg > test-decrypted.txt

# Compare
diff test.txt test-decrypted.txt
```

## Complete Backup Example with GPG

```bash
#!/bin/bash
# encrypted-backup.sh

# Configuration
IMAP_SERVER="imap.example.com"
IMAP_USER="user@example.com"
IMAP_PASS_FILE="/root/.imap_password"
GPG_RECIPIENT="backup@example.com"
S3_ENDPOINT="https://s3.hetzner.cloud"
S3_BUCKET="encrypted-email-backups"
S3_PREFIX="backups/$(date +%Y)/$(date +%m)/"
BACKUP_DIR="/tmp/email-backup"

echo "Starting encrypted backup at $(date)"

# Run backup with encryption
docker run --rm \
  -v "$BACKUP_DIR:/data" \
  -v ~/.gnupg:/root/.gnupg:ro \
  -v "$IMAP_PASS_FILE:/secrets/password:ro" \
  user2k20/imapbackup \
  -s "$IMAP_SERVER" \
  -u "$IMAP_USER" \
  -p @/secrets/password \
  -e \
  --s3-upload \
  --s3-endpoint="$S3_ENDPOINT" \
  --s3-bucket="$S3_BUCKET" \
  --s3-access-key="$S3_ACCESS_KEY" \
  --s3-secret-key="$S3_SECRET_KEY" \
  --s3-prefix="$S3_PREFIX" \
  --gpg-encrypt \
  --gpg-recipient="$GPG_RECIPIENT" \
  --nospinner

if [ $? -eq 0 ]; then
    echo "Backup completed successfully at $(date)"
    # Clean up local unencrypted files
    rm -rf "$BACKUP_DIR"/*
else
    echo "Backup failed at $(date)"
    exit 1
fi
```

## Key Management

### Trust Keys

```bash
# Edit key to set trust level
gpg --edit-key backup@example.com

# In GPG prompt:
gpg> trust
# Select: 5 = I trust ultimately
gpg> quit
```

### Renew Expiring Keys

```bash
# Edit key
gpg --edit-key backup@example.com

# Extend expiration
gpg> expire
# Select new expiration date
gpg> save
```

### Revoke a Compromised Key

```bash
# Generate revocation certificate
gpg --output revoke.asc --gen-revoke backup@example.com

# Import revocation (when needed)
gpg --import revoke.asc

# Publish to keyserver
gpg --send-keys <KEY_ID>
```

### Multiple Keys for Different Purposes

```bash
# Generate separate keys
gpg --full-generate-key  # For daily backups
gpg --full-generate-key  # For archival backups
gpg --full-generate-key  # For disaster recovery

# Use appropriate key
--gpg-recipient=daily-backup@example.com
--gpg-recipient=archive-backup@example.com
--gpg-recipient=dr-backup@example.com
```

## Best Practices

### 1. Use Strong Passphrases

```bash
# Generate strong passphrase
openssl rand -base64 32

# Use password manager to store it
```

### 2. Key Rotation

```bash
# Create new key annually
gpg --full-generate-key

# Re-encrypt old backups with new key
for file in *.gpg; do
    gpg --decrypt "$file" | gpg --encrypt --recipient new-backup@example.com > "new-$file"
done
```

### 3. Store Private Keys Securely

- Use hardware security keys (YubiKey, Nitrokey)
- Store offline in secure location
- Use encrypted USB drives
- Multiple backup locations

### 4. Document Key Information

```bash
# Create key documentation
cat > gpg-key-info.txt <<EOF
GPG Backup Key Information
==========================

Key ID: $(gpg --list-keys backup@example.com | grep pub | awk '{print $2}')
Email: backup@example.com
Created: $(date)
Fingerprint: $(gpg --fingerprint backup@example.com | grep fingerprint | awk -F= '{print $2}')
Location: ~/.gnupg and backed up to /secure-storage/gpg-backup/
Passphrase: Stored in password manager under "GPG Backup Key"

Recovery Instructions:
1. Import private key: gpg --import backup-private-key.asc
2. Import trust: gpg --import-ownertrust < ownertrust.txt
3. Test decryption: gpg --decrypt test.txt.gpg
EOF
```

### 5. Test Recovery Regularly

```bash
#!/bin/bash
# test-gpg-recovery.sh

echo "Testing GPG recovery process..."

# Create test backup
echo "Test data $(date)" > test-backup.txt
gpg --encrypt --recipient backup@example.com test-backup.txt

# Simulate fresh system
TEST_HOME=$(mktemp -d)
export GNUPGHOME="$TEST_HOME"

# Import keys
gpg --import backup-private-key.asc
gpg --import-ownertrust < ownertrust.txt

# Test decryption
gpg --decrypt test-backup.txt.gpg > recovered.txt

# Verify
if diff test-backup.txt recovered.txt; then
    echo "✓ Recovery test PASSED"
    rm -rf "$TEST_HOME"
    exit 0
else
    echo "✗ Recovery test FAILED"
    exit 1
fi
```

### 6. Monitor Key Expiration

```bash
# Check key expiration
gpg --list-keys backup@example.com | grep expires

# Set reminder before expiration
echo "Check GPG key expiration" | at now + 11 months
```

## Troubleshooting

### "No secret key" Error

```bash
# Verify private key exists
gpg --list-secret-keys

# Import if missing
gpg --import backup-private-key.asc
```

### Permission Denied

```bash
# Fix GPG directory permissions
chmod 700 ~/.gnupg
find ~/.gnupg -type f -exec chmod 600 {} \;
find ~/.gnupg -type d -exec chmod 700 {} \;
```

### "Unusable public key"

```bash
# Trust the key
gpg --edit-key backup@example.com
gpg> trust
gpg> 5
gpg> quit
```

### Docker Can't Access GPG

```bash
# Verify mount
docker run --rm -v ~/.gnupg:/root/.gnupg:ro alpine ls -la /root/.gnupg

# Check SELinux (if applicable)
chcon -Rt svirt_sandbox_file_t ~/.gnupg
```

## Security Checklist

- [ ] Generated strong 4096-bit RSA key
- [ ] Set strong passphrase on private key
- [ ] Backed up private key to secure location
- [ ] Backed up trust database
- [ ] Tested encryption and decryption
- [ ] Documented key information
- [ ] Stored passphrase in password manager
- [ ] Created revocation certificate
- [ ] Tested recovery procedure
- [ ] Set up key expiration monitoring

## Next Steps

- [S3 Setup](s3-setup.md) - Configure cloud storage
- [Backup Guide](backup-guide.md) - Create encrypted backups
- [Restore Guide](restore-guide.md) - Restore from encrypted backups
