# syntax=docker/dockerfile:1

# Multi-stage build for custom ERPNext with custom apps
ARG FRAPPE_VERSION=version-14
ARG ERPNEXT_VERSION=version-14
ARG PYTHON_VERSION=3.11
ARG NODE_VERSION=18

################################################################################
# Base stage - Install system dependencies
################################################################################
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Install system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    # Required for building Python packages
    gcc g++ make \
    # Frappe dependencies
    git curl wget \
    libffi-dev python3-dev python3-venv \
    libpq-dev mariadb-client default-libmysqlclient-dev \
    redis-tools \
    # Additional dependencies
    wkhtmltopdf \
    fonts-cantarell \
    xfonts-75dpi xfonts-base \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
ARG NODE_VERSION
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn \
    && rm -rf /var/lib/apt/lists/*

################################################################################
# Builder stage - Build Frappe bench with all apps
################################################################################
FROM base AS builder

ARG FRAPPE_VERSION
ARG ERPNEXT_VERSION

WORKDIR /home/frappe

# Install bench
RUN pip install --no-cache-dir frappe-bench \
    && bench init --version ${FRAPPE_VERSION} --frappe-branch ${FRAPPE_VERSION} \
    --python $(which python3) frappe-bench

WORKDIR /home/frappe/frappe-bench

# Get ERPNext
RUN bench get-app --branch ${ERPNEXT_VERSION} erpnext

# Copy custom apps from the repository
# The apps are in the root of this repo as directories
COPY erpnext ./apps/erpnext-custom
COPY frappe ./apps/frappe-custom
COPY healthcare ./apps/healthcare
COPY his ./apps/his
COPY hrms ./apps/hrms
COPY insights ./apps/insights
COPY rasiin_design ./apps/rasiin_design
COPY rasiin_hr ./apps/rasiin_hr
COPY frappe_whatsapp ./apps/frappe_whatsapp

# Install all apps' Python dependencies
RUN for app in apps/*; do \
    if [ -f "$app/requirements.txt" ]; then \
        pip install --no-cache-dir -r "$app/requirements.txt"; \
    fi; \
    done

# Build assets
RUN bench build --production

################################################################################
# Runtime stage - Create lean production image
################################################################################
FROM base AS runtime

# Create frappe user
RUN useradd -ms /bin/bash frappe

# Copy bench from builder
COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench /home/frappe/frappe-bench

WORKDIR /home/frappe/frappe-bench

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FRAPPE_SITE_NAME=site1.localhost

# Expose ports
EXPOSE 8000 9000 6787

USER frappe

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/method/ping || exit 1

# Default command
CMD ["bench", "start"]
