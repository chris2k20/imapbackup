# Docker Setup Guide

This guide explains how to use the `user2k20/imapbackup` Docker image for backing up and restoring your IMAP emails.

## Prerequisites

- Docker installed on your system
- IMAP server credentials (hostname, username, password)
- Optional: S3 credentials (for cloud storage)
- Optional: GPG keyring (for encryption)

## Basic Docker Usage

### Pull the Image

```bash
docker pull user2k20/imapbackup
```

### Run a Simple Backup

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e
```

You'll be prompted for the password interactively.

## Volume Mounts

### `/data` - Backup Directory (Required)

Mount a local directory to store your mbox backup files:

```bash
-v /path/to/local/backups:/data
```

Example:
```bash
-v $(pwd)/email-backups:/data
-v /home/user/mail-backups:/data
-v ~/Documents/backups:/data
```

### `/root/.gnupg` - GPG Keyring (Optional)

Required only if using GPG encryption:

```bash
-v ~/.gnupg:/root/.gnupg:ro
```

Note: Use `:ro` (read-only) for security if you only need decryption.

## Environment Variables

Instead of passing credentials as arguments, you can use environment variables:

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  -e IMAP_SERVER=imap.example.com \
  -e IMAP_USER=user@example.com \
  -e IMAP_PASS=yourpassword \
  user2k20/imapbackup \
  -s $IMAP_SERVER -u $IMAP_USER -p $IMAP_PASS -e
```

## Using Password Files

Store your password in a file for better security:

```bash
# Create password file
echo "your_password" > .imap_password
chmod 600 .imap_password

# Use with Docker
docker run --rm \
  -v $(pwd)/backups:/data \
  -v $(pwd)/.imap_password:/secrets/password:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p @/secrets/password \
  -e
```

## Docker Compose

Create a `docker-compose.yml` file for easier management:

```yaml
version: '3.8'

services:
  imap-backup:
    image: user2k20/imapbackup
    volumes:
      - ./backups:/data
      - ./.imap_password:/secrets/password:ro
      # Uncomment if using GPG
      # - ~/.gnupg:/root/.gnupg:ro
    environment:
      - IMAP_SERVER=imap.example.com
      - IMAP_USER=user@example.com
    command: >
      -s imap.example.com
      -u user@example.com
      -p @/secrets/password
      -e
```

Run with:
```bash
docker-compose run --rm imap-backup
```

## Advanced Docker Examples

### Backup Specific Folders

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p @/secrets/password \
  -e \
  -f "INBOX,Sent,Important"
```

### Backup with S3 Upload

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p yourpassword \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=my-backups \
  --s3-access-key=YOUR_ACCESS_KEY \
  --s3-secret-key=YOUR_SECRET_KEY
```

### Backup with S3 and GPG Encryption

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  -v ~/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://play.min.io:9000 \
  --s3-bucket=encrypted-backups \
  --s3-access-key=$MINIO_ACCESS_KEY \
  --s3-secret-key=$MINIO_SECRET_KEY \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com
```

### Restore from Local Backup

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -r \
  -s imap.newserver.com \
  -u user@newserver.com \
  -e
```

### Restore from S3 with GPG Decryption

```bash
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
  --s3-bucket=my-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com
```

## Automated Backups with Cron

### Create a Backup Script

```bash
#!/bin/bash
# backup-email.sh

docker run --rm \
  -v /backups/email:/data \
  -v /root/.gnupg:/root/.gnupg:ro \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -p @/root/.imap_password \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key="$S3_ACCESS_KEY" \
  --s3-secret-key="$S3_SECRET_KEY" \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com

echo "Backup completed at $(date)" >> /var/log/email-backup.log
```

Make it executable:
```bash
chmod +x backup-email.sh
```

### Add to Crontab

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup-email.sh

# Add weekly backup on Sundays at 3 AM
0 3 * * 0 /path/to/backup-email.sh
```

## Docker Compose with Cron

For scheduled backups using Docker Compose:

```yaml
version: '3.8'

services:
  imap-backup:
    image: user2k20/imapbackup
    volumes:
      - ./backups:/data
      - ~/.gnupg:/root/.gnupg:ro
    environment:
      - IMAP_SERVER=imap.example.com
      - IMAP_USER=user@example.com
      - S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - S3_SECRET_KEY=${S3_SECRET_KEY}
    command: >
      -s ${IMAP_SERVER}
      -u ${IMAP_USER}
      -p @/secrets/password
      -e
      --s3-upload
      --s3-endpoint=https://s3.hetzner.cloud
      --s3-bucket=email-backups
      --s3-access-key=${S3_ACCESS_KEY}
      --s3-secret-key=${S3_SECRET_KEY}
      --gpg-encrypt
      --gpg-recipient=backup@example.com
    restart: "no"

  backup-scheduler:
    image: mcuadros/ofelia:latest
    depends_on:
      - imap-backup
    command: daemon --docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    labels:
      ofelia.job-run.backup-email.schedule: "@daily"
      ofelia.job-run.backup-email.container: "imap-backup"
```

## Troubleshooting

### Permission Issues

If you encounter permission issues with volumes:

```bash
# Run with user permissions
docker run --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e
```

### GPG Permission Denied

Ensure GPG directory has correct permissions:

```bash
chmod 700 ~/.gnupg
chmod 600 ~/.gnupg/*
```

### View Container Logs

```bash
# Run in foreground to see output
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e
```

### Debug Mode

Add `--nospinner` flag for cleaner log output:

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --nospinner
```

## Best Practices

1. **Use Volume Mounts**: Always mount `/data` to persist backups
2. **Secure Passwords**: Use password files instead of command-line arguments
3. **Read-Only Mounts**: Use `:ro` for sensitive volumes when possible
4. **Environment Variables**: Store credentials in `.env` files
5. **Regular Testing**: Test restore procedures regularly
6. **Monitor Logs**: Keep logs of backup operations
7. **Verify Backups**: Periodically verify backup integrity

## Next Steps

- [Backup Guide](backup-guide.md) - Learn different backup strategies
- [S3 Setup](s3-setup.md) - Configure S3 storage providers
- [GPG Setup](gpg-setup.md) - Set up encryption
