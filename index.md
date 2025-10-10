---
layout: default
title: IMAP Backup & Restore Tool - Open Source Email Backup Solution
description: Free open-source Python tool for backing up and restoring IMAP email accounts. Features S3 cloud storage, GPG encryption, Docker support, and zero dependencies. Secure your emails today.
keywords: imap backup tool, email backup software, python imap backup, s3 email backup, gpg email encryption, docker email backup, open source backup, mailbox backup, email migration tool, imap restore
author: chris2k20
image: /imapbackup/assets/images/og-image.png
---

# IMAP Backup & Restore Tool

**The complete open-source solution for backing up, restoring, and migrating IMAP email accounts.**

[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/rcarmo/imapbackup.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/rcarmo/imapbackup/context:python)
[![Docker Pulls](https://img.shields.io/docker/pulls/user2k20/imapbackup)](https://hub.docker.com/r/user2k20/imapbackup)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Features

### Core Capabilities
- **📧 Full IMAP Backup** - Download all emails from any IMAP server to standard mbox format
- **🔄 Smart Restore** - Upload mbox files back to IMAP servers with duplicate detection
- **☁️ S3 Integration** - Store backups in S3-compatible storage (AWS S3, MinIO, Hetzner, Wasabi)
- **🔐 GPG Encryption** - Encrypt backups with GPG for secure storage
- **📦 Zero Dependencies** - Pure Python implementation, no external libraries required
- **🐳 Docker Ready** - Pre-built Docker image for easy deployment
- **⚡ Incremental Backups** - Only download new messages on subsequent runs
- **🔧 Flexible Key Import** - Import GPG keys from files, URLs, or environment variables

### Perfect For
- ✅ Email server migrations
- ✅ Automated daily backups
- ✅ Disaster recovery planning
- ✅ Compliance and archival
- ✅ Cloud storage integration
- ✅ Kubernetes deployments
- ✅ Personal email backup

---

## 📚 Quick Start

### Using Docker (Recommended)

```bash
# Basic backup
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e

# Backup with S3 upload and GPG encryption
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=https://example.com/keys/public.asc
```

### Using Python

```bash
# Clone repository
git clone https://github.com/chris2k20/imapbackup.git
cd imapbackup

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backup
python3 imapbackup.py -s imap.example.com -u user@example.com -e
```

---

## 📖 Documentation

### Getting Started
- **[Docker Setup Guide](docs/docker-setup.md)** - Quick start with Docker
- **[Python/venv Setup Guide](docs/python-setup.md)** - Installation with Python virtual environments
- **[Backup Guide](docs/backup-guide.md)** - Complete backup strategies and examples
- **[Restore Guide](docs/restore-guide.md)** - How to restore emails from backups

### Advanced Topics
- **[S3 Configuration](docs/s3-setup.md)** - Configure AWS S3, MinIO, Hetzner, and other providers
- **[GPG Encryption Guide](docs/gpg-setup.md)** - Set up encryption for secure backups
- **[GPG Key Import Guide](docs/gpg-key-import.md)** - Flexible key import from files, URLs, environment variables

---

## 🎯 Use Cases

### 1. Daily Automated Backups

```bash
# Cron job for daily backups at 2 AM
0 2 * * * docker run --rm -v /backups:/data user2k20/imapbackup \
  -s imap.example.com -u user@example.com -p @/root/.password -e \
  --s3-upload --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=backups --s3-access-key=$KEY --s3-secret-key=$SECRET
```

### 2. Email Server Migration

```bash
# Backup from old server
python3 imapbackup.py -s old.server.com -u user@old.com -e

# Restore to new server
python3 imapbackup.py -r -s new.server.com -u user@new.com -e
```

### 3. Kubernetes Deployment

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: email-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: user2k20/imapbackup:latest
            args:
              - -s
              - imap.example.com
              - -u
              - user@example.com
              - -e
              - --s3-upload
              - --gpg-encrypt
```

### 4. Encrypted Cloud Backups

```bash
# Backup with encryption - no GPG keyring mount needed!
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.gmail.com -u myemail@gmail.com -e \
  --s3-upload --s3-bucket=secure-backups \
  --gpg-encrypt --gpg-recipient=backup@example.com \
  --gpg-import-key=env:GPG_PUBLIC_KEY
```

---

## 💡 Why Choose IMAP Backup Tool?

### Open Source & Free
- **MIT Licensed** - Use it anywhere, modify it freely
- **No Vendor Lock-in** - Standard mbox format works with any email client
- **Community Driven** - Actively maintained since 2007

### Production Ready
- **Zero Dependencies** - Pure Python, runs anywhere Python 3.6+ is available
- **Battle Tested** - Used by thousands of users worldwide
- **Docker Official** - Pre-built images on Docker Hub
- **Kubernetes Ready** - Perfect for cloud-native deployments

### Security First
- **Read-Only IMAP Operations** - Never modifies source emails during backup
- **GPG Encryption** - Industry-standard OpenPGP encryption
- **S3 Compatible** - Works with all major cloud providers
- **Flexible Key Management** - Import keys from files, URLs, or environment variables

### Developer Friendly
- **Clean Code** - Well-documented Python codebase
- **Comprehensive Docs** - Detailed guides for every use case
- **Easy Integration** - Simple CLI interface, scriptable
- **Active Support** - GitHub issues and pull requests welcome

---

## 🌟 Popular Use Cases & Keywords

**Email Backup Solutions**: Perfect for Gmail backup, Office 365 backup, Exchange backup, Outlook backup, and any IMAP-compatible email service.

**Server Migration**: Seamlessly migrate emails between providers - move from Gmail to ProtonMail, Office 365 to Google Workspace, or any IMAP server to another.

**Compliance & Archival**: Meet GDPR, HIPAA, and other regulatory requirements with encrypted email archives stored securely in S3-compatible storage.

**Disaster Recovery**: Automated daily backups ensure you never lose important emails. Restore to any IMAP server in minutes.

**Self-Hosted Email**: Perfect companion for self-hosted mail servers using Dovecot, Postfix, Zimbra, or any IMAP-compatible server.

---

## 📊 Command Line Options

### Basic Options
- `-s HOST` - IMAP server hostname
- `-u USER` - Username/email address
- `-p PASS` - Password or `@/path/to/file` to read from file
- `-e` - Use SSL/TLS (recommended)
- `-d DIR` - Directory for mbox files

### Backup/Restore Modes
- `-a` - Append mode (default, incremental backups)
- `-y` - Overwrite mode (full backup)
- `-r` - Restore mode (upload to IMAP server)

### Folder Selection
- `-f FOLDERS` - Backup specific folders (comma-separated)
- `--exclude-folders=FOLDERS` - Exclude specific folders

### S3 Storage Options
- `--s3-upload` - Enable S3 integration
- `--s3-endpoint=URL` - S3 endpoint URL
- `--s3-bucket=BUCKET` - S3 bucket name
- `--s3-access-key=KEY` - S3 access key
- `--s3-secret-key=KEY` - S3 secret key
- `--s3-prefix=PREFIX` - Optional S3 path prefix

### GPG Encryption Options
- `--gpg-encrypt` - Enable GPG encryption/decryption
- `--gpg-recipient=EMAIL` - GPG key ID or email address
- `--gpg-import-key=SOURCE` - Import public key from:
  - File: `/path/to/key.asc`
  - URL: `https://example.com/key.asc`
  - Environment: `env:GPG_PUBLIC_KEY`

---

## 🛠️ Supported Platforms & Services

### IMAP Servers
- Gmail / Google Workspace
- Microsoft 365 / Outlook.com
- ProtonMail
- Fastmail
- Zoho Mail
- Apple iCloud Mail
- Yahoo Mail
- Self-hosted (Dovecot, Postfix, Zimbra, etc.)
- Any IMAP-compatible server

### S3-Compatible Storage
- **AWS S3** - Amazon Web Services
- **Hetzner Storage Box** - European data centers
- **MinIO** - Self-hosted object storage
- **Wasabi** - Hot cloud storage
- **Backblaze B2** - Affordable cloud storage
- **DigitalOcean Spaces** - Simple object storage
- **Cloudflare R2** - Zero egress fees

### Deployment Options
- **Docker** - Pre-built image: `user2k20/imapbackup`
- **Docker Compose** - Easy multi-container setups
- **Kubernetes** - CronJob examples included
- **Python venv** - Isolated Python environment
- **Bare Metal** - Direct Python execution
- **Cron** - Traditional Unix scheduling

---

## 🚦 Requirements

### For Docker
- Docker installed
- That's it! Everything else is included in the image

### For Python
- Python 3.6 or higher (tested with 3.8+)
- GPG (for encryption): `apt install gnupg`
- Python dependencies: `pip install -r requirements.txt`

---

## 🔗 Links

- **[GitHub Repository](https://github.com/chris2k20/imapbackup)** - Source code and issues
- **[Docker Hub](https://hub.docker.com/r/user2k20/imapbackup)** - Pre-built Docker images
- **[Documentation](docs/README.md)** - Complete guides and examples
- **[License](LICENSE)** - MIT License

---

## 📈 SEO Keywords

imap backup, email backup tool, python imap, backup imap emails, gmail backup, office 365 backup, email migration, imap restore, mailbox backup, mbox backup, docker email backup, s3 email backup, encrypted email backup, gpg email encryption, automated email backup, email archival, email disaster recovery, open source email backup, imap sync, email server migration, dovecot backup, postfix backup, kubernetes email backup, cloud email backup, secure email backup

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, fork the repository, and create pull requests.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Originally developed around 2007 and actively maintained ever since. Thanks to all contributors who have helped make this tool better over the years.

---

**⭐ Star this repository if you find it useful!**

**🐛 Found a bug? [Open an issue](https://github.com/chris2k20/imapbackup/issues)**

**💬 Have questions? [Check the documentation](docs/README.md)**
