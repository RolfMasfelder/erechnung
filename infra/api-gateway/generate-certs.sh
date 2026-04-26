#!/bin/bash
# Generiert selbst-signierte SSL-Zertifikate mit CA für lokale Entwicklung

set -e

CERT_DIR="$(dirname "$0")/certs"
DAYS=3650  # 10 Jahre

echo "Generiere CA und SSL-Zertifikate für localhost..."

# 1. CA (Certificate Authority) erstellen
echo "Schritt 1: Erstelle lokale CA..."

cat > "${CERT_DIR}/ca.cnf" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_ca

[dn]
C=DE
ST=Germany
L=Development
O=eRechnung Development
OU=Certificate Authority
CN=eRechnung Local CA

[v3_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
EOF

# CA Private Key
openssl genrsa -out "${CERT_DIR}/ca.key" 2048

# CA Zertifikat (selbst-signiert)
openssl req -new -x509 \
    -days ${DAYS} \
    -key "${CERT_DIR}/ca.key" \
    -out "${CERT_DIR}/ca.crt" \
    -config "${CERT_DIR}/ca.cnf"

echo "✅ CA erstellt: ${CERT_DIR}/ca.crt"

# 2. Server-Zertifikat erstellen
echo "Schritt 2: Erstelle Server-Zertifikat..."

cat > "${CERT_DIR}/server.cnf" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=DE
ST=Germany
L=Development
O=eRechnung Development
OU=Development
CN=localhost

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
DNS.2 = api-gateway
DNS.3 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Server Private Key
openssl genrsa -out "${CERT_DIR}/localhost.key" 2048

# Certificate Signing Request (CSR)
openssl req -new \
    -key "${CERT_DIR}/localhost.key" \
    -out "${CERT_DIR}/localhost.csr" \
    -config "${CERT_DIR}/server.cnf"

# Server-Zertifikat von CA signieren lassen
openssl x509 -req \
    -days ${DAYS} \
    -in "${CERT_DIR}/localhost.csr" \
    -CA "${CERT_DIR}/ca.crt" \
    -CAkey "${CERT_DIR}/ca.key" \
    -CAcreateserial \
    -out "${CERT_DIR}/localhost.crt" \
    -extensions v3_req \
    -extfile "${CERT_DIR}/server.cnf"

# Berechtigungen setzen
chmod 644 "${CERT_DIR}/ca.crt"
chmod 600 "${CERT_DIR}/ca.key"
chmod 644 "${CERT_DIR}/localhost.crt"
chmod 600 "${CERT_DIR}/localhost.key"

echo ""
echo "✅ Zertifikate erfolgreich erstellt:"
echo "   📁 CA-Zertifikat:     ${CERT_DIR}/ca.crt"
echo "   📁 Server-Zertifikat: ${CERT_DIR}/localhost.crt"
echo "   🔑 Server-Key:        ${CERT_DIR}/localhost.key"
echo ""
echo "🔧 Firefox-Import (empfohlen):"
echo "   1. Firefox: Einstellungen → Datenschutz & Sicherheit → Zertifikate"
echo "   2. 'Zertifikate anzeigen' → Tab 'Zertifizierungsstellen'"
echo "   3. 'Importieren' → ${CERT_DIR}/ca.crt"
echo "   4. ✅ 'Dieser CA vertrauen, um Websites zu identifizieren'"
echo ""
echo "🔧 Chrome-Import:"
echo "   1. Einstellungen → Datenschutz und Sicherheit → Sicherheit"
echo "   2. 'Zertifikate verwalten' → 'Zertifizierungsstellen'"
echo "   3. 'Importieren' → ${CERT_DIR}/ca.crt"
echo ""
echo "Zertifikat-Details:"
openssl x509 -in "${CERT_DIR}/localhost.crt" -text -noout | grep -A2 "Subject:"
