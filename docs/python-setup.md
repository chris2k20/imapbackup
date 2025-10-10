# Python Virtual Environment Setup

Guide for setting up and running imapbackup with Python virtual environments.

## Why Use a Virtual Environment?

Virtual environments (venv) provide:
- Isolated Python dependencies
- No conflicts with system packages
- Easy dependency management
- Reproducible environments
- Clean uninstall (just delete the venv folder)

## Quick Start

```bash
# Clone or navigate to the repository
cd /path/to/imapbackup

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (GPG)
sudo apt install gnupg  # Ubuntu/Debian

# Run backup
python3 imapbackup38.py -s imap.example.com -u user@example.com -e

# Deactivate when done
deactivate
```

## Detailed Setup

### 1. Prerequisites

**Python 3.6 or higher:**
```bash
# Check Python version
python3 --version

# If not installed:
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv python3-pip

# RHEL/CentOS
sudo yum install python3 python3-pip

# macOS (using Homebrew)
brew install python3
```

### 2. Create Virtual Environment

```bash
# Navigate to project directory
cd /path/to/imapbackup

# Create venv
python3 -m venv venv

# Verify creation
ls -la venv/
```

This creates a `venv/` directory containing:
- `bin/` - Python interpreter and scripts (Linux/macOS)
- `Scripts/` - Python interpreter and scripts (Windows)
- `lib/` - Installed packages
- `include/` - C headers

### 3. Activate Virtual Environment

**Linux/macOS:**
```bash
source venv/bin/activate

# Your prompt will change to show (venv)
(venv) user@host:~/imapbackup$
```

**Windows (cmd.exe):**
```cmd
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Fish shell:**
```fish
source venv/bin/activate.fish
```

### 4. Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install from requirements.txt
pip install -r requirements.txt

# Verify installation
pip list
```

Expected packages:
- `awscli` - For S3 operations
- Dependencies of awscli (botocore, s3transfer, etc.)

### 5. Install System Dependencies

**GPG (for encryption):**

```bash
# Ubuntu/Debian
sudo apt install gnupg

# RHEL/CentOS/Fedora
sudo yum install gnupg2

# Arch Linux
sudo pacman -S gnupg

# macOS
brew install gnupg

# Verify installation
gpg --version
```

### 6. Verify Setup

```bash
# Check Python is from venv
which python3
# Should show: /path/to/imapbackup/venv/bin/python3

# Check AWS CLI
aws --version

# Check GPG
gpg --version

# Test the script
python3 imapbackup38.py --help
```

## Running Backups

### Basic Backup

```bash
# Activate venv
source venv/bin/activate

# Run backup
python3 imapbackup38.py \
  -s imap.example.com \
  -u user@example.com \
  -e

# Deactivate when done
deactivate
```

### With S3 Upload

```bash
source venv/bin/activate

python3 imapbackup38.py \
  -s imap.example.com \
  -u user@example.com \
  -e \
  --s3-upload \
  --s3-endpoint=https://s3.hetzner.cloud \
  --s3-bucket=email-backups \
  --s3-access-key=$S3_KEY \
  --s3-secret-key=$S3_SECRET

deactivate
```

### With GPG Encryption

```bash
source venv/bin/activate

python3 imapbackup38.py \
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

deactivate
```

## Scripting with Virtual Environment

### Backup Script

```bash
#!/bin/bash
# backup-email.sh

# Activate virtual environment
source /path/to/imapbackup/venv/bin/activate

# Run backup
python3 /path/to/imapbackup/imapbackup38.py \
  -s imap.example.com \
  -u user@example.com \
  -p @/root/.imap_password \
  -e \
  -d /backups/email

# Deactivate
deactivate

echo "Backup completed at $(date)"
```

Make it executable:
```bash
chmod +x backup-email.sh
```

### Cron Job

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup-email.sh >> /var/log/email-backup.log 2>&1
```

### Systemd Service

Create `/etc/systemd/system/email-backup.service`:

```ini
[Unit]
Description=Email Backup Service
After=network.target

[Service]
Type=oneshot
User=backupuser
WorkingDirectory=/home/backupuser/imapbackup
ExecStart=/home/backupuser/imapbackup/venv/bin/python3 /home/backupuser/imapbackup/imapbackup38.py -s imap.example.com -u user@example.com -p @/home/backupuser/.imap_password -e -d /backups/email

[Install]
WantedBy=multi-user.target
```

Create timer `/etc/systemd/system/email-backup.timer`:

```ini
[Unit]
Description=Email Backup Timer
Requires=email-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable email-backup.timer
sudo systemctl start email-backup.timer

# Check status
sudo systemctl status email-backup.timer
sudo systemctl list-timers
```

## Managing the Virtual Environment

### Update Dependencies

```bash
source venv/bin/activate

# Update all packages
pip list --outdated
pip install --upgrade awscli

# Or update from requirements.txt
pip install --upgrade -r requirements.txt

deactivate
```

### Freeze Current Dependencies

```bash
source venv/bin/activate

# Export current package versions
pip freeze > requirements-frozen.txt

deactivate
```

### Recreate Virtual Environment

```bash
# Remove old venv
rm -rf venv/

# Create new venv
python3 -m venv venv

# Activate and install
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### Add to .gitignore

```bash
# Add to .gitignore
echo "venv/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
```

## Troubleshooting

### "python3: command not found"

```bash
# Install Python
sudo apt install python3  # Ubuntu/Debian
sudo yum install python3  # RHEL/CentOS
```

### "No module named venv"

```bash
# Install venv module
sudo apt install python3-venv  # Ubuntu/Debian
```

### "pip: command not found"

```bash
# Install pip
sudo apt install python3-pip  # Ubuntu/Debian
sudo yum install python3-pip  # RHEL/CentOS
```

### Virtual Environment Not Activating

**PowerShell Execution Policy (Windows):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Wrong Python Version:**
```bash
# Create venv with specific Python version
python3.9 -m venv venv
```

### AWS CLI Not Working

```bash
source venv/bin/activate

# Verify awscli installation
pip show awscli

# Reinstall if needed
pip uninstall awscli
pip install awscli

# Test
aws --version
```

### GPG Not Found

```bash
# Install GPG
sudo apt install gnupg

# Verify
which gpg
gpg --version
```

### Permission Errors

```bash
# Ensure proper ownership
sudo chown -R $USER:$USER venv/

# Ensure proper permissions
chmod -R u+rwX venv/
```

## Best Practices

### 1. Always Use Virtual Environments

```bash
# ✓ Good
source venv/bin/activate
python3 imapbackup38.py ...

# ✗ Bad (pollutes system Python)
sudo pip install awscli
python3 imapbackup38.py ...
```

### 2. Pin Dependency Versions

```bash
# Create locked requirements
pip freeze > requirements-lock.txt

# Install from locked requirements
pip install -r requirements-lock.txt
```

### 3. Document Your Setup

Create `SETUP.md`:
```markdown
# Setup Instructions

1. Python version: 3.9.2
2. Virtual environment location: `./venv`
3. Dependencies: See `requirements.txt`
4. System dependencies: gnupg 2.2.19
5. Backup location: `/backups/email`
```

### 4. Use Environment Variables

```bash
# Create .env file
cat > .env <<EOF
IMAP_SERVER=imap.example.com
IMAP_USER=user@example.com
S3_ENDPOINT=https://s3.hetzner.cloud
S3_BUCKET=email-backups
EOF

chmod 600 .env

# Load in script
source .env
python3 imapbackup38.py -s "$IMAP_SERVER" -u "$IMAP_USER" ...
```

### 5. Separate Development and Production

```bash
# Development requirements
cat > requirements-dev.txt <<EOF
-r requirements.txt
pytest
black
flake8
EOF

# Install dev dependencies
pip install -r requirements-dev.txt
```

## Alternative: Using virtualenvwrapper

For easier venv management:

```bash
# Install virtualenvwrapper
pip install virtualenvwrapper

# Add to ~/.bashrc or ~/.zshrc
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

# Create venv
mkvirtualenv imapbackup

# Activate
workon imapbackup

# Deactivate
deactivate

# Delete
rmvirtualenv imapbackup
```

## Alternative: Using conda

If you prefer conda:

```bash
# Create conda environment
conda create -n imapbackup python=3.9

# Activate
conda activate imapbackup

# Install dependencies
pip install -r requirements.txt

# Deactivate
conda deactivate
```

## Comparison: Docker vs Virtual Environment

| Feature | Docker | Virtual Environment |
|---------|--------|---------------------|
| Isolation | Full system isolation | Python packages only |
| Setup time | Pull image (fast) | Install dependencies |
| Disk space | ~200MB (image) | ~50MB (venv) |
| Portability | Excellent | Good (requires Python) |
| System deps | Included | Manual install |
| Complexity | Medium | Low |
| Best for | Production, automation | Development, testing |

**When to use Docker:**
- Production deployments
- CI/CD pipelines
- Multiple users
- Need full isolation

**When to use venv:**
- Development
- Single user systems
- Customization needed
- Learning the code

## Next Steps

- [Docker Setup](docker-setup.md) - Alternative Docker approach
- [Backup Guide](backup-guide.md) - Create your first backup
- [S3 Setup](s3-setup.md) - Configure cloud storage
