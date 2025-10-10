# 📧 IMAP Backup & Restore

[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/rcarmo/imapbackup.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/rcarmo/imapbackup/context:python)
[![Docker Pulls](https://img.shields.io/docker/pulls/user2k20/imapbackup)](https://hub.docker.com/r/user2k20/imapbackup)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**The complete open-source solution for backing up, restoring, and migrating IMAP email accounts.**

Zero dependencies. Pure Python. Docker ready. S3 compatible. GPG encrypted.

---

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Simple backup
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com -u user@example.com -e

# With S3 upload and GPG encryption (no keyring needed!)
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.gmail.com -u myemail@gmail.com -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=https://example.com/keys/public.asc
```

### Using Python

```bash
# Clone and setup
git clone https://github.com/chris2k20/imapbackup.git
cd imapbackup
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backup
python3 imapbackup.py -s imap.example.com -u user@example.com -e
```

---

## ✨ Features

### Core Features
- 📦 **Zero Dependencies** - Pure Python, no external libraries required
- 🔄 **Incremental Backups** - Only downloads new messages on subsequent runs
- 🐳 **Docker Ready** - Pre-built image: `user2k20/imapbackup`
- ☁️ **S3 Compatible** - Works with AWS S3, MinIO, Hetzner, Wasabi, Backblaze
- 🔐 **GPG Encryption** - Encrypt backups with flexible key import
- 📧 **Universal IMAP** - Works with Gmail, Office 365, ProtonMail, and any IMAP server
- 🔁 **Restore Mode** - Upload mbox files back to IMAP servers
- 📁 **Standard mbox Format** - Import into any email client

### New Features ✨
- 📋 **Multi-Account Backup** - Backup multiple accounts with YAML configuration
- 🔑 **Flexible GPG Key Import** - Import keys from files, URLs, or environment variables
- 🚫 **No Keyring Mounting** - Encrypt without mounting `~/.gnupg` in Docker
- ☸️ **Kubernetes Ready** - Perfect for cloud-native deployments
- 🔒 **Safe Operations** - Only performs read operations on source IMAP

---

## 📚 Documentation

### Getting Started
- **[Docker Setup Guide](docs/docker-setup.md)** - Get started with Docker in 5 minutes
- **[Python Setup Guide](docs/python-setup.md)** - Virtual environment installation
- **[Backup Guide](docs/backup-guide.md)** - Complete backup strategies
- **[Restore Guide](docs/restore-guide.md)** - How to restore emails

### Advanced
- **[Multi-Account Backup](docs/multi-account-setup.md)** - Backup multiple accounts with YAML config 🆕
- **[S3 Configuration](docs/s3-setup.md)** - Configure cloud storage
- **[GPG Encryption](docs/gpg-setup.md)** - Secure your backups
- **[GPG Key Import](docs/gpg-key-import.md)** - Flexible key management 🆕

📖 **[View Full Documentation](docs/README.md)**

---

## 🎯 Common Use Cases

### Daily Automated Backups

```bash
# Cron job for daily backups at 2 AM
0 2 * * * docker run --rm -v /backups:/data user2k20/imapbackup \
  -s imap.example.com -u user@example.com -p @/root/.password -e \
  --s3-upload --s3-bucket=backups --s3-access-key=$KEY --s3-secret-key=$SECRET
```

### Email Server Migration

```bash
# Step 1: Backup from old server
python3 imapbackup.py -s old.server.com -u user@old.com -e

# Step 2: Restore to new server
python3 imapbackup.py -r -s new.server.com -u user@new.com -e
```

### Kubernetes CronJob

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
              - --gpg-import-key=env:GPG_PUBLIC_KEY
```

### Encrypted Cloud Backups (No Keyring Mounting!)

```bash
# Export your public key once
export GPG_PUBLIC_KEY=$(cat ~/keys/public.asc)

# Backup with encryption - no GPG keyring mount needed!
docker run --rm \
  -v $(pwd)/backups:/data \
  -e GPG_PUBLIC_KEY \
  user2k20/imapbackup \
  -s imap.gmail.com -u myemail@gmail.com -e \
  --s3-upload --s3-bucket=secure-backups \
  --gpg-encrypt --gpg-recipient=backup@example.com \
  --gpg-import-key=env:GPG_PUBLIC_KEY
```

### Multi-Account Backup 🆕

```bash
# Create config.yaml
cat > config.yaml <<EOF
global:
  basedir: ./backups
  s3:
    enabled: true
    endpoint: https://s3.hetzner.cloud
    bucket: email-backups
  gpg:
    enabled: true
    recipient: backup@example.com

accounts:
  - name: personal-gmail
    server: imap.gmail.com
    user: myemail@gmail.com
    pass: env:GMAIL_PASSWORD

  - name: work-office365
    server: outlook.office365.com
    user: user@company.com
    pass: env:WORK_PASSWORD
EOF

# Backup all accounts - auto-detects config.yaml
python3 imapbackup.py

# Or explicitly specify config file
python3 imapbackup.py --config=config.yaml
```

**Note:** If `config.yaml` or `config.yml` exists in the current directory, it will be automatically used when running without arguments.

See **[Multi-Account Setup Guide](docs/multi-account-setup.md)** for complete documentation.

---

## 🛠️ Command Line Options

### Basic Options
```
-s HOST              IMAP server hostname
-u USER              Username/email address
-p PASS              Password or @/path/to/file
-e                   Use SSL/TLS (recommended)
-d DIR               Directory for mbox files
```

### Backup/Restore Modes
```
-a                   Append mode (default, incremental)
-y                   Overwrite mode (full backup)
-r                   Restore mode (upload to IMAP)
```

### Multi-Account Mode 🆕
```
--config=FILE        Load settings from YAML config file
                     Allows backing up multiple accounts
                     See config.example.yaml for format

                     Auto-detection: If no arguments are provided,
                     the script automatically looks for config.yaml
                     or config.yml in the current directory
```

### Folder Selection
```
-f FOLDERS           Backup specific folders (comma-separated)
--exclude-folders    Exclude specific folders
```

### S3 Storage
```
--s3-upload          Enable S3 integration
--s3-endpoint=URL    S3 endpoint URL
--s3-bucket=NAME     Bucket name
--s3-access-key=KEY  Access key
--s3-secret-key=KEY  Secret key
--s3-prefix=PATH     Optional path prefix
```

### GPG Encryption 🆕
```
--gpg-encrypt                Enable GPG encryption/decryption
--gpg-recipient=EMAIL        GPG key ID or email
--gpg-import-key=SOURCE      Import public key from:
                             - File: /path/to/key.asc
                             - URL: https://example.com/key.asc
                             - Env: env:GPG_PUBLIC_KEY
```

---

## 🌟 Why Choose This Tool?

### Battle Tested
- **Since 2007** - Over 15 years of active development
- **Production Ready** - Used by thousands worldwide
- **Zero Dependencies** - Pure Python, runs anywhere

### Feature Rich
- **Incremental Backups** - Fast subsequent runs
- **S3 Compatible** - Works with all major cloud providers
- **GPG Encryption** - Industry-standard security
- **Docker First** - Container-native design

### Flexible & Modern
- **No Keyring Mounting** 🆕 - Import GPG keys from anywhere
- **Kubernetes Ready** - Perfect for cloud deployments
- **Environment Variables** - 12-factor app compliant
- **CI/CD Friendly** - Easy automation

---

## 🚦 Requirements

### For Docker
- Docker installed
- That's it! Everything else is included

### For Python
- Python 3.6+ (tested with 3.8+)
- GPG (for encryption): `apt install gnupg`
- Dependencies: `pip install -r requirements.txt`

---

## 💡 What's New

### v2.0 Features 🆕

#### Multi-Account Configuration
Backup multiple email accounts with a single YAML configuration file:
- **Global Settings**: Define common S3, GPG, and connection settings once
- **Account-Specific Overrides**: Customize per-account as needed
- **Auto Directory Structure**: Each account gets its own subdirectory
- **Auto S3 Prefixes**: Automatic prefix generation per account
- **Flexible Passwords**: Support for direct, file-based, and environment variables

See **[Multi-Account Setup Guide](docs/multi-account-setup.md)** for complete documentation.

#### Flexible GPG Key Import
No more mounting GPG keyrings! Import public keys from:
- **Files**: `--gpg-import-key=/etc/public-key.asc`
- **URLs**: `--gpg-import-key=https://example.com/key.asc`
- **Environment**: `--gpg-import-key=env:GPG_PUBLIC_KEY`

Perfect for Docker, Kubernetes, and CI/CD pipelines!

#### S3 Integration
Upload backups to any S3-compatible storage:
- AWS S3
- Hetzner Storage Box
- MinIO (self-hosted)
- Wasabi, Backblaze B2, DigitalOcean Spaces

#### Restore Mode
Migrate emails between servers:
```bash
python3 imapbackup.py -r -s new-server.com -u user@example.com -e
```

---

## 🔗 Links

- **📖 [Documentation](docs/README.md)** - Complete guides and examples
- **🐳 [Docker Hub](https://hub.docker.com/r/user2k20/imapbackup)** - Pre-built images
- **🐛 [Issues](https://github.com/chris2k20/imapbackup/issues)** - Report bugs
- **🤝 [Contributing](CONTRIBUTING.md)** - How to contribute

---

## 🌍 Supported Platforms

### IMAP Servers
✅ Gmail / Google Workspace
✅ Microsoft 365 / Outlook.com
✅ ProtonMail
✅ Fastmail, Zoho, Yahoo
✅ iCloud Mail
✅ Self-hosted (Dovecot, Postfix, Zimbra)
✅ Any IMAP-compatible server

### S3 Storage
✅ AWS S3
✅ Hetzner Storage Box
✅ MinIO (self-hosted)
✅ Wasabi Hot Cloud Storage
✅ Backblaze B2
✅ DigitalOcean Spaces
✅ Cloudflare R2

### Deployment
✅ Docker / Docker Compose
✅ Kubernetes CronJobs
✅ Python venv
✅ Cron jobs
✅ Systemd services
✅ GitHub Actions / GitLab CI

---

## 🎓 Examples

### Backup Gmail to Hetzner S3 (Encrypted)

```bash
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.gmail.com \
  -u myemail@gmail.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.eu-central-1.hetzner.cloud \
  --s3-bucket=gmail-backups \
  --s3-access-key=$HETZNER_KEY \
  --s3-secret-key=$HETZNER_SECRET \
  --gpg-encrypt \
  --gpg-recipient=backup@example.com \
  --gpg-import-key=https://raw.githubusercontent.com/you/keys/main/public.asc
```

### Backup Office 365 to MinIO (Local)

```bash
python3 imapbackup.py \
  -s outlook.office365.com \
  -u user@company.com \
  -e \
  --s3-upload \
  --s3-endpoint=http://minio.local:9000 \
  --s3-bucket=email-backups \
  --s3-access-key=minioadmin \
  --s3-secret-key=minioadmin
```

### Backup Specific Folders Only

```bash
docker run --rm -v $(pwd)/backups:/data \
  user2k20/imapbackup \
  -s imap.example.com \
  -u user@example.com \
  -e \
  -f "INBOX,Sent,Important,Projects"
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to:
- 🐛 Report bugs via [Issues](https://github.com/chris2k20/imapbackup/issues)
- 💡 Suggest features
- 🔧 Submit pull requests
- 📖 Improve documentation

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

Free to use, modify, and distribute. No warranties provided.

---

## 🙏 Acknowledgments

Originally developed around 2007 by [Rui Carmo](http://taoofmac.com/space/projects/imapbackup) and actively maintained ever since.

Special thanks to all [contributors](https://github.com/chris2k20/imapbackup/graphs/contributors) who have helped make this tool better over the years.

---

## 📞 Support

- 📖 **Documentation**: [docs/README.md](docs/README.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/chris2k20/imapbackup/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/chris2k20/imapbackup/discussions)

---

**⭐ Star this repository if you find it useful!**

**📢 Share with others who need email backup solutions!**

---

## 📊 Quick Comparison

| Feature | This Tool | Gmail Takeout | Mail Clients |
|---------|-----------|---------------|--------------|
| **Incremental** | ✅ Yes | ❌ No | ⚠️ Sometimes |
| **Automated** | ✅ Yes | ❌ Manual | ⚠️ Limited |
| **S3 Upload** | ✅ Yes | ❌ No | ❌ No |
| **GPG Encryption** | ✅ Yes | ❌ No | ❌ No |
| **Restore** | ✅ Yes | ⚠️ Import only | ✅ Yes |
| **Docker** | ✅ Yes | ❌ No | ❌ No |
| **Standard Format** | ✅ mbox | ⚠️ Proprietary | ⚠️ Varies |
| **Open Source** | ✅ MIT | ❌ No | ⚠️ Varies |

---

<div align="center">

**Made with ❤️ by the open-source community**

[📖 Documentation](docs/README.md) • [🐳 Docker Hub](https://hub.docker.com/r/user2k20/imapbackup) • [🐛 Report Issue](https://github.com/chris2k20/imapbackup/issues) • [⭐ Star on GitHub](https://github.com/chris2k20/imapbackup)

</div>
