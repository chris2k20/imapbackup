# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Build-time args for labeling
ARG GIT_SHA=unknown
ARG GITHUB_REPOSITORY=unknown

# Environment for reliable Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install minimal runtime deps
# - tini: proper signal handling (PID 1)
# - gnupg: optional GPG encryption used by the script
# - ca-certificates: sane TLS defaults
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tini gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Optional S3 support via AWS CLI (pure Python, multi-arch friendly)
RUN pip install --no-cache-dir awscli

# Create non-root user and working dirs
RUN useradd -r -u 10001 -m app \
    && mkdir -p /app /data \
    && chown -R app:app /app /data

# Copy ONLY the requested script
WORKDIR /app
COPY imapbackup38.py /app/imapbackup38.py
RUN chmod +x /app/imapbackup38.py

USER app

# Default data directory where mboxes will be written (mount a volume here)
WORKDIR /data
VOLUME ["/data"]

# OCI labels
LABEL org.opencontainers.image.title="imapbackup" \
      org.opencontainers.image.description="IMAP incremental backup tool packaged as a container. Runs imapbackup38.py only." \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/${GITHUB_REPOSITORY}" \
      org.opencontainers.image.revision="${GIT_SHA}"

# Use tini as entrypoint and forward args to the script
ENTRYPOINT ["tini","--","/app/imapbackup38.py"]
