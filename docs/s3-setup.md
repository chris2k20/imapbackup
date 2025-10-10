# S3 Storage Configuration Guide

Complete guide for setting up S3-compatible storage for email backups.

## Table of Contents

- [Supported S3 Providers](#supported-s3-providers)
- [MinIO Setup](#minio-setup)
- [Hetzner S3 Setup](#hetzner-s3-setup)
- [AWS S3 Setup](#aws-s3-setup)
- [Wasabi Setup](#wasabi-setup)
- [DigitalOcean Spaces Setup](#digitalocean-spaces-setup)
- [Best Practices](#best-practices)

## Supported S3 Providers

The tool supports any S3-compatible storage provider:

- **MinIO** (Self-hosted)
- **Hetzner Cloud** (Germany-based, GDPR compliant)
- **AWS S3** (Amazon)
- **Wasabi** (Cost-effective)
- **DigitalOcean Spaces**
- **Backblaze B2** (via S3 compatible API)
- **Cloudflare R2**
- Any other S3-compatible service

## MinIO Setup

MinIO is an open-source, self-hosted S3-compatible storage.

### Install MinIO

```bash
# Docker installation
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -v $(pwd)/minio-data:/data \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=your-secure-password \
  minio/minio server /data --console-address ":9001"
```

### Create Bucket

```bash
# Install MinIO client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure MinIO client
mc alias set myminio http://localhost:9000 admin your-secure-password

# Create bucket
mc mb myminio/email-backups

# Set bucket policy (optional - for public read)
mc anonymous set download myminio/email-backups
```

### Use with imapbackup

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=http://your-minio-server:9000 \
  --s3-bucket=email-backups \
  --s3-access-key=admin \
  --s3-secret-key=your-secure-password
```

### Docker Compose with MinIO

```yaml
version: '3.8'

services:
  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ./minio-data:/data
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    command: server /data --console-address ":9001"

  email-backup:
    image: user2k20/imapbackup
    depends_on:
      - minio
    volumes:
      - ./backups:/data
    environment:
      - IMAP_SERVER=imap.example.com
      - IMAP_USER=user@example.com
    command: >
      -s imap.example.com
      -u user@example.com
      -p @/secrets/password
      -e
      --s3-upload
      --s3-endpoint=http://minio:9000
      --s3-bucket=email-backups
      --s3-access-key=admin
      --s3-secret-key=${MINIO_PASSWORD}
```

## Hetzner S3 Setup

Hetzner offers S3-compatible object storage in Europe.

### Create Storage Box

1. Log in to [Hetzner Cloud Console](https://console.hetzner.cloud/)
2. Navigate to "Storage" → "Object Storage"
3. Create a new Object Storage
4. Select region (e.g., `eu-central-1`)
5. Generate access keys

### Configuration

```bash
# Hetzner S3 endpoints by region:
# eu-central-1: https://s3.eu-central-1.hetzner.cloud
# us-east-1: https://s3.us-east-1.hetzner.cloud

docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.hetzner.cloud \
  --s3-bucket=my-email-backups \
  --s3-access-key=YOUR_HETZNER_ACCESS_KEY \
  --s3-secret-key=YOUR_HETZNER_SECRET_KEY
```

### Bucket Management

```bash
# Using AWS CLI with Hetzner
export AWS_ACCESS_KEY_ID=YOUR_HETZNER_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_HETZNER_SECRET_KEY

# List buckets
aws s3 ls --endpoint-url=https://s3.eu-central-1.hetzner.cloud

# Create bucket
aws s3 mb s3://my-email-backups --endpoint-url=https://s3.eu-central-1.hetzner.cloud

# List objects
aws s3 ls s3://my-email-backups/ --endpoint-url=https://s3.eu-central-1.hetzner.cloud
```

## AWS S3 Setup

Amazon S3 is the original and most widely used S3 service.

### Create IAM User

1. Log in to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to IAM → Users
3. Create new user with programmatic access
4. Attach policy: `AmazonS3FullAccess` (or create custom policy)
5. Save access key and secret key

### Create Bucket

```bash
# Using AWS CLI
aws s3 mb s3://my-email-backups --region us-east-1

# Set lifecycle policy (optional - auto-delete old backups)
cat > lifecycle.json <<EOF
{
  "Rules": [{
    "Id": "DeleteOldBackups",
    "Status": "Enabled",
    "Prefix": "daily/",
    "Expiration": {
      "Days": 30
    }
  }]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket my-email-backups \
  --lifecycle-configuration file://lifecycle.json
```

### Configuration

```bash
docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.us-east-1.amazonaws.com \
  --s3-bucket=my-email-backups \
  --s3-access-key=$AWS_ACCESS_KEY_ID \
  --s3-secret-key=$AWS_SECRET_ACCESS_KEY
```

### Enable Versioning (Recommended)

```bash
aws s3api put-bucket-versioning \
  --bucket my-email-backups \
  --versioning-configuration Status=Enabled
```

## Wasabi Setup

Wasabi offers cost-effective S3-compatible storage.

### Create Account and Bucket

1. Sign up at [Wasabi](https://wasabi.com/)
2. Create access keys
3. Create bucket in desired region

### Configuration

```bash
# Wasabi endpoints by region:
# us-east-1: https://s3.us-east-1.wasabisys.com
# us-east-2: https://s3.us-east-2.wasabisys.com
# us-west-1: https://s3.us-west-1.wasabisys.com
# eu-central-1: https://s3.eu-central-1.wasabisys.com

docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.wasabisys.com \
  --s3-bucket=email-backups \
  --s3-access-key=YOUR_WASABI_ACCESS_KEY \
  --s3-secret-key=YOUR_WASABI_SECRET_KEY
```

## DigitalOcean Spaces Setup

DigitalOcean Spaces provides S3-compatible object storage.

### Create Space

1. Log in to [DigitalOcean](https://cloud.digitalocean.com/)
2. Navigate to Spaces
3. Create new Space
4. Generate Spaces access keys

### Configuration

```bash
# DigitalOcean Spaces endpoints:
# nyc3: https://nyc3.digitaloceanspaces.com
# sfo3: https://sfo3.digitaloceanspaces.com
# ams3: https://ams3.digitaloceanspaces.com
# sgp1: https://sgp1.digitaloceanspaces.com
# fra1: https://fra1.digitaloceanspaces.com

docker run --rm \
  -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://fra1.digitaloceanspaces.com \
  --s3-bucket=email-backups \
  --s3-access-key=YOUR_DO_SPACES_KEY \
  --s3-secret-key=YOUR_DO_SPACES_SECRET
```

## Best Practices

### 1. Use Environment Variables

```bash
# Create .env file
cat > .env <<EOF
S3_ENDPOINT=https://s3.eu-central-1.hetzner.cloud
S3_BUCKET=email-backups
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_PREFIX=backups/$(date +%Y)/$(date +%m)/
EOF

chmod 600 .env

# Use in docker-compose.yml
version: '3.8'
services:
  backup:
    image: user2k20/imapbackup
    env_file: .env
    volumes:
      - ./backups:/data
    command: >
      -s imap.example.com -u user@example.com -e
      --s3-upload
      --s3-endpoint=${S3_ENDPOINT}
      --s3-bucket=${S3_BUCKET}
      --s3-access-key=${S3_ACCESS_KEY}
      --s3-secret-key=${S3_SECRET_KEY}
      --s3-prefix=${S3_PREFIX}
```

### 2. Organize with Prefixes

```bash
# Daily backups
--s3-prefix=daily/$(date +%Y-%m-%d)/

# Monthly archives
--s3-prefix=monthly/$(date +%Y-%m)/

# Per-user backups
--s3-prefix=users/user@example.com/

# Versioned backups
--s3-prefix=v2/backups/$(date +%Y)/
```

### 3. Enable Server-Side Encryption

For AWS S3:
```bash
aws s3api put-bucket-encryption \
  --bucket my-email-backups \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### 4. Set Up Lifecycle Policies

```bash
# Auto-delete daily backups after 30 days
cat > lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldDailyBackups",
      "Status": "Enabled",
      "Prefix": "daily/",
      "Expiration": {"Days": 30}
    },
    {
      "Id": "ArchiveMonthlyBackups",
      "Status": "Enabled",
      "Prefix": "monthly/",
      "Transitions": [{
        "Days": 90,
        "StorageClass": "GLACIER"
      }]
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket my-email-backups \
  --lifecycle-configuration file://lifecycle.json \
  --endpoint-url=https://s3.your-provider.com
```

### 5. Monitor Storage Usage

```bash
# Check bucket size (AWS)
aws s3 ls s3://my-email-backups --recursive --summarize --human-readable

# Monitor with CloudWatch (AWS)
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=my-email-backups \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average
```

### 6. Set Up Alerts

```bash
# Example: Email alert when bucket size > 100GB
# (Depends on provider - AWS CloudWatch example)
aws cloudwatch put-metric-alarm \
  --alarm-name email-backup-size-alarm \
  --alarm-description "Alert when backup size exceeds 100GB" \
  --metric-name BucketSizeBytes \
  --namespace AWS/S3 \
  --statistic Average \
  --period 86400 \
  --threshold 107374182400 \
  --comparison-operator GreaterThanThreshold
```

### 7. Implement Backup Verification

```bash
#!/bin/bash
# verify-s3-backup.sh

ENDPOINT="https://s3.hetzner.cloud"
BUCKET="email-backups"
TODAY=$(date +%Y-%m-%d)

# Check if today's backup exists
aws s3 ls s3://$BUCKET/daily/$TODAY/ --endpoint-url=$ENDPOINT

if [ $? -eq 0 ]; then
    echo "Backup verification SUCCESS for $TODAY"
    exit 0
else
    echo "Backup verification FAILED for $TODAY"
    # Send alert email
    echo "Backup failed" | mail -s "Backup Alert" admin@example.com
    exit 1
fi
```

## Cost Optimization

### Storage Costs Comparison (approx. 2024)

| Provider | Storage ($/GB/month) | Transfer Out ($/GB) | Notes |
|----------|---------------------|---------------------|-------|
| Hetzner | €0.002 (~$0.002) | €0.012 (~$0.012) | EU-based |
| Wasabi | $0.0059 | Free (up to storage) | Min. 90 days |
| AWS S3 | $0.023 | $0.09 | First 1GB free |
| MinIO | Hardware cost only | Free | Self-hosted |
| DO Spaces | $0.02 | $0.01 | First 1TB free |

### Calculate Your Costs

```bash
# Estimate backup size
du -sh /path/to/backups

# Calculate monthly cost
# Example: 50GB backup on Hetzner
# Storage: 50 * 0.002 = $0.10/month
# No download cost for backups

# On AWS S3:
# Storage: 50 * 0.023 = $1.15/month
# Download (once): 50 * 0.09 = $4.50
```

## Troubleshooting

### Connection Errors

```bash
# Test endpoint connectivity
curl -I https://s3.hetzner.cloud

# Verify credentials
aws s3 ls --endpoint-url=https://s3.hetzner.cloud

# Check DNS resolution
nslookup s3.hetzner.cloud
```

### Authentication Errors

- Verify access key and secret key
- Check bucket name spelling
- Ensure IAM permissions (for AWS)
- Verify endpoint URL format

### Upload Failures

- Check network bandwidth
- Verify bucket exists
- Check bucket permissions
- Monitor disk space on local system

## Next Steps

- [GPG Setup](gpg-setup.md) - Add encryption to S3 backups
- [Backup Guide](backup-guide.md) - Create backup strategies
- [Docker Setup](docker-setup.md) - Automate with Docker
