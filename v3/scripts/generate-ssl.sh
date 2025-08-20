#!/bin/bash

# =============================================================================
# SSL Certificate Generation Script for SEED Production
# =============================================================================

set -e

DOMAIN=${1:-"your-domain.com"}
SSL_DIR="./config/nginx/ssl"
DAYS=${2:-365}

echo "Generating SSL certificate for domain: $DOMAIN"
echo "Certificate will be valid for $DAYS days"

# Create SSL directory
mkdir -p "$SSL_DIR"

# Generate private key
echo "Generating private key..."
openssl genrsa -out "$SSL_DIR/server.key" 2048

# Generate certificate signing request
echo "Generating certificate signing request..."
openssl req -new -key "$SSL_DIR/server.key" -out "$SSL_DIR/server.csr" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"

# Generate self-signed certificate (for development/testing)
echo "Generating self-signed certificate..."
openssl x509 -req -in "$SSL_DIR/server.csr" -signkey "$SSL_DIR/server.key" \
    -out "$SSL_DIR/server.crt" -days "$DAYS" \
    -extensions v3_req -extfile <(
    echo '[v3_req]'
    echo 'basicConstraints = CA:FALSE'
    echo 'keyUsage = nonRepudiation, digitalSignature, keyEncipherment'
    echo "subjectAltName = DNS:$DOMAIN,DNS:*.$DOMAIN,IP:127.0.0.1"
)

# Set proper permissions
chmod 600 "$SSL_DIR/server.key"
chmod 644 "$SSL_DIR/server.crt"

# Clean up CSR
rm "$SSL_DIR/server.csr"

echo "SSL certificate generated successfully!"
echo "Certificate: $SSL_DIR/server.crt"
echo "Private key: $SSL_DIR/server.key"
echo ""
echo "For production, replace with Let's Encrypt certificate:"
echo "  certbot certonly --standalone -d $DOMAIN"
echo ""
echo "Or use your own CA-signed certificate"