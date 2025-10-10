---
layout: default
title: GPG Key Import Guide - Flexible Public Key Management
description: Learn how to import GPG public keys from files, URLs, and environment variables for Docker and Kubernetes email backups. No keyring mounting needed.
keywords: gpg key import, docker gpg, kubernetes gpg, environment variable gpg, gpg automation, flexible key management, gpg docker encryption
---

# GPG Public Key Import - Flexible Options

The IMAP backup tool now supports importing GPG public keys from multiple sources, making it easier to use encryption without manually managing GPG keyrings.

## Overview

When using GPG encryption (`--gpg-encrypt`), you can now automatically import public keys from:
- **Files** (local paths)
- **URLs** (HTTPS/HTTP)
- **Environment variables**

This is especially useful for Docker containers and automation where you don't want to mount GPG keyrings.

## Use Cases

### 1. **Embed Public Key in Docker Image**

The simplest approach for automated backups:

```dockerfile
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y gnupg awscli curl && \
    rm -rf /var/lib/apt/lists/*

# Copy application
COPY imapbackup.py /usr/local/bin/imapbackup
RUN chmod +x /usr/local/bin/imapbackup

# Copy and import GPG public key (safe to include in image)
COPY public-key.asc /etc/gpg-backup-key.asc
RUN gpg --import /etc/gpg-backup-key.asc

WORKDIR /data
ENTRYPOINT ["/usr/local/bin/imapbackup"]
```

**Or use the auto-import feature:**

```dockerfile
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y gnupg awscli curl && \
    rm -rf /var/lib/apt/lists/*

# Copy application
COPY imapbackup.py /usr/local/bin/imapbackup
RUN chmod +x /usr/local/bin/imapbackup

# Copy public key (will be auto-imported on first run)
COPY public-key.asc /etc/gpg-backup-key.asc

WORKDIR /data
ENTRYPOINT ["/usr/local/bin/imapbackup"]
```

Then run:

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=/etc/gpg-backup-key.asc
```

### 2. **Download Public Key from URL**

Host your public key on a web server and download it automatically:

```bash
# Export your public key once
gpg --armor --export backup@example.com > public-key.asc

# Upload to a web server (GitHub, your own server, etc.)
# Then use in backups:

docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=https://example.com/keys/backup-public.asc
```

**GitHub example:**

```bash
# Store your public key in a GitHub repository
# Then reference it:

--gpg-import-key=https://raw.githubusercontent.com/youruser/keys/main/backup-public.asc
```

### 3. **Environment Variable (Docker/Kubernetes)**

Pass the public key as an environment variable:

**Docker:**

```bash
# Export your public key
export GPG_PUBLIC_KEY=$(cat public-key.asc)

# Run with environment variable
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
```

**Docker Compose:**

```yaml
version: '3.8'

services:
  email-backup:
    image: user2k20/imapbackup
    volumes:
      - ./backups:/data
    environment:
      - GPG_PUBLIC_KEY=${GPG_PUBLIC_KEY}
    command: >
      -s imap.example.com
      -u user@example.com
      -p @/run/secrets/imap_password
      -e
      --s3-upload
      --s3-endpoint=https://s3.hetzner.cloud
      --s3-bucket=backups
      --s3-access-key=${S3_ACCESS_KEY}
      --s3-secret-key=${S3_SECRET_KEY}
      --gpg-encrypt
      --gpg-recipient=backup@example.com
      --gpg-import-key=env:GPG_PUBLIC_KEY
    secrets:
      - imap_password

secrets:
  imap_password:
    file: ./imap_password.txt
```

**Kubernetes:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gpg-public-key
data:
  public-key.asc: |
    -----BEGIN PGP PUBLIC KEY BLOCK-----
    ... your public key here ...
    -----END PGP PUBLIC KEY BLOCK-----
---
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
            image: user2k20/imapbackup
            command:
            - /usr/local/bin/imapbackup
            - -s
            - imap.example.com
            - -u
            - user@example.com
            - -e
            - --s3-upload
            - --s3-endpoint=https://s3.hetzner.cloud
            - --s3-bucket=backups
            - --s3-access-key=$(S3_ACCESS_KEY)
            - --s3-secret-key=$(S3_SECRET_KEY)
            - --gpg-encrypt
            - --gpg-recipient=backup@example.com
            - --gpg-import-key=/etc/gpg/public-key.asc
            env:
            - name: S3_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: access-key
            - name: S3_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: secret-key
            volumeMounts:
            - name: gpg-key
              mountPath: /etc/gpg
              readOnly: true
            - name: backup-data
              mountPath: /data
          volumes:
          - name: gpg-key
            configMap:
              name: gpg-public-key
          - name: backup-data
            emptyDir: {}
          restartPolicy: OnFailure
```

### 4. **Local File Path**

Simple file-based approach:

```bash
# Export your public key
gpg --armor --export backup@example.com > ~/keys/backup-public.asc

# Use it in backup
python3 imapbackup.py \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=~/keys/backup-public.asc
```

## Export Your Public Key

Before using any of these methods, you need to export your GPG public key:

### Check Existing Keys

```bash
gpg --list-keys
```

### Generate a New Key (if needed)

```bash
gpg --full-generate-key
```

Choose:
- Key type: RSA and RSA (default)
- Key size: 4096 bits (recommended)
- Expiration: Choose based on your security policy
- User ID: backup@example.com (or your email)

### Export Public Key

```bash
# ASCII armored format (recommended for files/URLs/env vars)
gpg --armor --export backup@example.com > public-key.asc

# Verify the export
cat public-key.asc
```

You should see:
```
-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBGX...
...
-----END PGP PUBLIC KEY BLOCK-----
```

## Command-Line Syntax

```
--gpg-import-key=SOURCE
```

Where `SOURCE` can be:

| Source Type | Format | Example |
|------------|---------|---------|
| **File path** | `/path/to/key.asc` or `~/path` | `--gpg-import-key=/etc/gpg-public-key.asc` |
| **URL** | `https://...` or `http://...` | `--gpg-import-key=https://example.com/key.asc` |
| **Environment** | `env:VARIABLE_NAME` | `--gpg-import-key=env:GPG_PUBLIC_KEY` |

## Security Considerations

### Public Key (Safe to Share)
- ✅ **Safe** to include in Docker images
- ✅ **Safe** to store in version control
- ✅ **Safe** to host on public URLs
- ✅ **Safe** to pass as environment variables
- **Purpose**: Only used for **encryption**
- **Cannot** decrypt data

### Private Key (Keep Secret!)
- ❌ **NEVER** include in Docker images
- ❌ **NEVER** commit to version control
- ❌ **NEVER** host on public URLs
- ❌ **NEVER** pass as environment variables (except in secure contexts)
- **Purpose**: Used for **decryption**
- **Must** be kept secret and secure

### For Restore/Decryption

When you need to **restore** (decrypt), you still need the private key:

```bash
# Restore requires private key - must mount GPG keyring
docker run --rm \
  -v $(pwd)/backups:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -r \
  -s imap.newserver.com \
  -u user@newserver.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com
```

## Troubleshooting

### Key Import Fails

**"Failed to download key from URL"**
- Check URL is accessible: `curl -I https://example.com/key.asc`
- Verify HTTPS certificate is valid
- Ensure `curl` or `wget` is installed in container

**"Environment variable not found"**
- Check variable is set: `echo $GPG_PUBLIC_KEY`
- Use correct syntax: `env:GPG_PUBLIC_KEY` (not `$GPG_PUBLIC_KEY`)
- In Docker, ensure variable is passed with `-e` flag

**"Invalid GPG key format"**
- Verify key starts with `-----BEGIN PGP PUBLIC KEY BLOCK-----`
- Use `--armor` when exporting: `gpg --armor --export ...`
- Check for line ending issues (especially on Windows)

### Encryption Fails After Import

**"No public key"**
- Verify import succeeded (check output for "Successfully imported")
- List imported keys: `gpg --list-keys`
- Ensure `--gpg-recipient` matches key email/ID

**"Untrusted key"**
- This is normal for encryption-only operations
- Script uses `--trust-model always` for automation
- For manual GPG operations, trust the key: `gpg --edit-key backup@example.com` then `trust`

## Complete Examples

### Example 1: GitHub-hosted Key with Hetzner S3

```bash
#!/bin/bash
# Daily backup script

docker run --rm \
  -v /backups/email:/data \
  user2k20/imapbackup \
  -s imap.gmail.com \
  -u myemail@gmail.com \
  -p @/root/.gmail_password \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.hetzner.cloud \
  --s3-bucket=email-backups-encrypted \
  --s3-access-key=$HETZNER_S3_KEY \
  --s3-secret-key=$HETZNER_S3_SECRET \
  --s3-prefix=gmail-backup/ \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=https://raw.githubusercontent.com/myuser/keys/main/backup-public.asc
```

### Example 2: Environment Variable with MinIO

```bash
# Export the key once
export GPG_PUBLIC_KEY=$(cat ~/keys/backup-public.asc)

# Run backup
docker run --rm \
  -v $(pwd)/backups:/data \
  -e GPG_PUBLIC_KEY \
  user2k20/imapbackup \
  -s mail.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://minio.example.com \
  --s3-bucket=email-backups \
  --s3-access-key=minioadmin \
  --s3-secret-key=minioadmin \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=env:GPG_PUBLIC_KEY
```

### Example 3: File in Docker Image

```bash
# Build custom image with embedded public key
cat > Dockerfile <<EOF
FROM user2k20/imapbackup:latest

# Add your public key
COPY backup-public.asc /etc/backup-key.asc
EOF

docker build -t my-email-backup .

# Run without needing to specify key location every time
docker run --rm \
  -v $(pwd)/backups:/data \
  my-email-backup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=/etc/backup-key.asc \
  --s3-upload \
  --s3-endpoint=https://s3.wasabisys.com \
  --s3-bucket=backups \
  --s3-access-key=$WASABI_KEY \
  --s3-secret-key=$WASABI_SECRET
```

## Workflow Recommendation

**For Automated Backups (Encryption):**
1. Generate GPG keypair once
2. Export public key: `gpg --armor --export backup@example.com > public-key.asc`
3. Use `--gpg-import-key` with any source (file/URL/env)
4. Backups encrypt automatically

**For Restore (Decryption):**
1. Keep private key secure on restore machine
2. Mount GPG keyring: `-v ~/.gnupg:/root/.gnupg:ro`
3. Run restore mode with `-r` flag
4. Script decrypts automatically using mounted private key

## Benefits of This Approach

1. **No GPG Keyring Management**: Don't need to mount `~/.gnupg` for backups
2. **Docker-Friendly**: Easily embed keys in images or pass as env vars
3. **Kubernetes-Ready**: Use ConfigMaps for public keys
4. **CI/CD Compatible**: Store public keys in CI secrets
5. **Flexible Sources**: Choose what works best for your infrastructure
6. **Secure**: Public keys are safe to distribute
