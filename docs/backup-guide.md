# Backup Guide

Complete guide for backing up your IMAP emails using the imapbackup tool.

## Table of Contents

- [Basic Backups](#basic-backups)
- [Incremental Backups](#incremental-backups)
- [Selective Backups](#selective-backups)
- [Cloud Backups](#cloud-backups)
- [Encrypted Backups](#encrypted-backups)
- [Best Practices](#best-practices)
- [Kubernetes](#kubernetes)

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

## Kubernetes

Run scheduled backups and ad-hoc restores in Kubernetes using the Docker image. The container entrypoint is `/app/imapbackup38.py`, so you pass flags as container args.

### Prerequisites

- Create a namespace (example: `email-backups`).
- Create a Secret with your IMAP password (and optional S3 credentials).
- Optionally create a PersistentVolumeClaim (PVC) to store mbox files.

Example secrets and PVC:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: email-backups
---
apiVersion: v1
kind: Secret
metadata:
  name: imapbackup-secrets
  namespace: email-backups
type: Opaque
stringData:
  imap_password: "your_imap_password"
  # Optional if using S3 uploads from the CronJob/Job
  s3_access_key: "REPLACE_ME"
  s3_secret_key: "REPLACE_ME"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: imapbackup-pvc
  namespace: email-backups
spec:
  accessModes: [ "ReadWriteOnce" ]
  resources:
    requests:
      storage: 20Gi
```

### Daily backup CronJob (PVC storage)

Backs up to a mounted PVC at `/data` every night at 03:00. Uses SSL and disables the spinner for cleaner logs.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: imapbackup-daily
  namespace: email-backups
spec:
  schedule: "0 3 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsNonRoot: true
            fsGroup: 10001
          containers:
            - name: imapbackup
              image: user2k20/imapbackup:latest
              imagePullPolicy: IfNotPresent
              args:
                - -s
                - imap.example.com
                - -u
                - user@example.com
                - -p
                - @/secrets/password
                - -e
                - --nospinner
                - -d
                - /data
              volumeMounts:
                - name: data
                  mountPath: /data
                - name: secrets
                  mountPath: /secrets
                  readOnly: true
          volumes:
            - name: data
              persistentVolumeClaim:
                claimName: imapbackup-pvc
            - name: secrets
              secret:
                secretName: imapbackup-secrets
                items:
                  - key: imap_password
                    path: password
```

### Daily backup CronJob (S3 upload, no PVC)

Uploads backups directly to S3-compatible storage. Uses `sh -c` to pass secret values as CLI flags.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: imapbackup-daily-s3
  namespace: email-backups
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsNonRoot: true
          containers:
            - name: imapbackup
              image: user2k20/imapbackup:latest
              imagePullPolicy: IfNotPresent
              command: ["sh","-c"]
              args:
                - >-
                  /app/imapbackup38.py
                  -s imap.example.com -u user@example.com -p @/secrets/password -e --nospinner
                  --s3-upload --s3-endpoint=https://s3.example.com --s3-bucket=email-backups
                  --s3-access-key "$S3_ACCESS_KEY" --s3-secret-key "$S3_SECRET_KEY"
                  --s3-prefix "daily/$(date +%F)/" -d /data
              env:
                - name: S3_ACCESS_KEY
                  valueFrom:
                    secretKeyRef:
                      name: imapbackup-secrets
                      key: s3_access_key
                - name: S3_SECRET_KEY
                  valueFrom:
                    secretKeyRef:
                      name: imapbackup-secrets
                      key: s3_secret_key
              volumeMounts:
                - name: secrets
                  mountPath: /secrets
                  readOnly: true
                - name: data
                  emptyDir: {}
          volumes:
            - name: secrets
              secret:
                secretName: imapbackup-secrets
                items:
                  - key: imap_password
                    path: password
            - name: data
              emptyDir: {}
```

### Restore Job (from PVC)

Restores previously saved mbox files from a PVC to the IMAP server using restore mode (`-r`).

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: imaprestore-pvc
  namespace: email-backups
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        fsGroup: 10001
      containers:
        - name: imaprestore
          image: user2k20/imapbackup:latest
          args:
            - -r
            - -s
            - imap.example.com
            - -u
            - user@example.com
            - -p
            - @/secrets/password
            - -e
            - --nospinner
            - -d
            - /data
          volumeMounts:
            - name: data
              mountPath: /data
            - name: secrets
              mountPath: /secrets
              readOnly: true
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: imapbackup-pvc
        - name: secrets
          secret:
            secretName: imapbackup-secrets
            items:
              - key: imap_password
                path: password
```

### Restore Job (download from S3, then restore)

Uses an initContainer to download mbox files from S3 into `/data` before running restore.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: imaprestore-s3
  namespace: email-backups
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
      initContainers:
        - name: fetch-from-s3
          image: user2k20/imapbackup:latest
          command: ["sh","-c"]
          args:
            - >-
              AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
              aws s3 cp s3://email-backups/restore-set/ /data --recursive --endpoint-url https://s3.example.com
          env:
            - name: S3_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: imapbackup-secrets
                  key: s3_access_key
            - name: S3_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: imapbackup-secrets
                  key: s3_secret_key
          volumeMounts:
            - name: data
              mountPath: /data
      containers:
        - name: imaprestore
          image: user2k20/imapbackup:latest
          args:
            - -r
            - -s
            - imap.example.com
            - -u
            - user@example.com
            - -p
            - @/secrets/password
            - -e
            - --nospinner
            - -d
            - /data
          volumeMounts:
            - name: data
              mountPath: /data
            - name: secrets
              mountPath: /secrets
              readOnly: true
      volumes:
        - name: data
          emptyDir: {}
        - name: secrets
          secret:
            secretName: imapbackup-secrets
            items:
              - key: imap_password
                path: password
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
