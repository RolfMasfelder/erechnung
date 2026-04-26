#!/bin/bash
# Entrypoint wrapper: copies TLS certificates with correct permissions
# before delegating to the standard PostgreSQL entrypoint.
set -e

CERT_SRC="/var/lib/postgresql/certs-mounted"
CERT_DST="/var/lib/postgresql/certs"

if [ -f "$CERT_SRC/server.crt" ] && [ -f "$CERT_SRC/server.key" ]; then
    mkdir -p "$CERT_DST"
    cp "$CERT_SRC/server.crt" "$CERT_DST/server.crt"
    cp "$CERT_SRC/server.key" "$CERT_DST/server.key"
    [ -f "$CERT_SRC/ca.crt" ] && cp "$CERT_SRC/ca.crt" "$CERT_DST/ca.crt"

    # PostgreSQL requires key owned by postgres user with mode 600
    chown postgres:postgres "$CERT_DST"/*
    chmod 600 "$CERT_DST/server.key"
    chmod 644 "$CERT_DST/server.crt"
    [ -f "$CERT_DST/ca.crt" ] && chmod 644 "$CERT_DST/ca.crt"

    echo "✓ TLS certificates installed with correct permissions"
fi

# Delegate to standard PostgreSQL entrypoint
exec docker-entrypoint.sh "$@"
