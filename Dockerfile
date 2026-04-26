FROM python:3.14-slim-bookworm AS base

# Build arguments for versioning
ARG APP_VERSION=1.0.0
ARG BUILD_DATE=unknown
ARG GIT_SHA=unknown

# OCI image labels
LABEL org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.title="eRechnung" \
      org.opencontainers.image.description="ZUGFeRD/Factur-X Rechnungssystem"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    DJANGO_SETTINGS_MODULE="invoice_project.settings" \
    TZ=Europe/Berlin \
    IS_DOCKER=true \
    BUILD_DATE=${BUILD_DATE} \
    GIT_SHA=${GIT_SHA}

WORKDIR /app

# Install system dependencies, create user, and set up directories in one layer
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    gettext \
    ghostscript \
    libpq-dev \
    postgresql-client \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && userdel -r appuser 2>/dev/null || true \
    && groupdel appuser 2>/dev/null || true \
    && groupadd -g 1234 app_group \
    && useradd -u 1234 -g app_group -s /bin/bash -m app_user \
    && mkdir -p /app/project_root/media/invoices /app/project_root/media/xml /app/project_root/media/company_logos /app/static /app/logs \
    && chown -R app_user:app_group /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base AS development
ENV DEBUG=True
COPY --chown=app_user:app_group . .
# Ensure project_root directory is fully writable by app_user
RUN chown -R app_user:app_group /app/project_root \
    && chmod -R 755 /app/project_root \
    && mkdir -p /app/project_root/media/invoices /app/project_root/media/xml /app/project_root/media/company_logos \
    && mkdir -p /app/project_root/static \
    && chown -R app_user:app_group /app/project_root/media /app/project_root/static
USER app_user
EXPOSE 8000
CMD ["python", "project_root/manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM base AS production
ENV DEBUG=False

COPY --chown=app_user:app_group . .
# Ensure project_root directory is fully writable by app_user
# Create media subdirectories for PDF and XML storage (needed for tests and runtime)
RUN chown -R app_user:app_group /app/project_root \
    && chmod -R 755 /app/project_root \
    && mkdir -p /app/project_root/media/invoices /app/project_root/media/xml /app/project_root/media/company_logos \
    && chown -R app_user:app_group /app/project_root/media
USER app_user

# Minimal env for build-time collectstatic
# These values are only for the image build; runtime env comes from Compose/.env
ARG BUILD_DJANGO_SECRET_KEY="build-secret-not-used-at-runtime"
ENV DJANGO_SECRET_KEY=${BUILD_DJANGO_SECRET_KEY} \
    POSTGRES_DB=build \
    POSTGRES_USER=build \
    POSTGRES_PASSWORD=build \
    POSTGRES_HOST=localhost \
    POSTGRES_PORT=5432 \
    DJANGO_ALLOWED_HOSTS=*

# Collect static files
RUN python project_root/manage.py collectstatic --no-input

EXPOSE 8000
CMD ["gunicorn", "--chdir", "project_root", "--bind", "0.0.0.0:8000", "--workers", "4", "invoice_project.wsgi:application"]
