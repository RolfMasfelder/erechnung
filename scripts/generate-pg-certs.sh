#!/bin/bash
# Generate self-signed TLS certificates for PostgreSQL (Docker Compose development)
# These certs are for local development ONLY — k3s uses cert-manager.
set -euo pipefail

CERT_DIR="${1:-infra/postgres/certs}"

mkdir -p "$CERT_DIR"

# Generate CA key and certificate
openssl req -new -x509 -days 3650 -nodes \
    -out "$CERT_DIR/ca.crt" \
    -keyout "$CERT_DIR/ca.key" \
    -subj "/CN=eRechnung Dev CA"

# Generate server key and CSR
openssl req -new -nodes \
    -out "$CERT_DIR/server.csr" \
    -keyout "$CERT_DIR/server.key" \
    -subj "/CN=db"

# Sign server certificate with CA (SAN includes Docker Compose service names)
openssl x509 -req -in "$CERT_DIR/server.csr" \
    -CA "$CERT_DIR/ca.crt" \
    -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$CERT_DIR/server.crt" \
    -days 3650 \
    -extfile <(printf "subjectAltName=DNS:db,DNS:localhost,DNS:postgres-service,IP:127.0.0.1")

# PostgreSQL requires server.key to be readable only by owner
chmod 600 "$CERT_DIR/server.key"
# CA key should also be restricted
chmod 600 "$CERT_DIR/ca.key"

# Clean up CSR and serial
rm -f "$CERT_DIR/server.csr" "$CERT_DIR/ca.srl"

echo "✓ PostgreSQL TLS certificates generated in $CERT_DIR"
echo "  CA:          $CERT_DIR/ca.crt"
echo "  Server cert: $CERT_DIR/server.crt"
echo "  Server key:  $CERT_DIR/server.key"
