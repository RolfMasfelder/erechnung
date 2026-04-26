#!/bin/bash
# Setup TLS for PostgreSQL if certificates are mounted.
# This script runs as part of docker-entrypoint-initdb.d (runs on first DB init).
# For already-initialized databases, the command-line args in docker-compose.yml
# or Kubernetes deployment handle SSL enablement.
set -e

CERT_DIR="/var/lib/postgresql/certs"

if [ -f "$CERT_DIR/server.crt" ] && [ -f "$CERT_DIR/server.key" ]; then
    echo "TLS certificates found — configuring PostgreSQL for SSL"

    # Ensure correct ownership and permissions (PostgreSQL requires this)
    cp "$CERT_DIR/server.crt" /var/lib/postgresql/server.crt
    cp "$CERT_DIR/server.key" /var/lib/postgresql/server.key
    chown postgres:postgres /var/lib/postgresql/server.crt /var/lib/postgresql/server.key
    chmod 600 /var/lib/postgresql/server.key
    chmod 644 /var/lib/postgresql/server.crt

    if [ -f "$CERT_DIR/ca.crt" ]; then
        cp "$CERT_DIR/ca.crt" /var/lib/postgresql/ca.crt
        chown postgres:postgres /var/lib/postgresql/ca.crt
        chmod 644 /var/lib/postgresql/ca.crt
    fi

    echo "✓ TLS certificates installed for PostgreSQL"
else
    echo "No TLS certificates found at $CERT_DIR — SSL not configured"
fi
