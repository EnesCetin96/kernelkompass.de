#!/bin/bash
# Certbot ile Let's Encrypt sertifikası al
# Önkoşul: docker compose up -d çalışıyor olmalı, DNS yayılmış olmalı
set -e

DOMAIN="kernelkompass.de"
EMAIL="SENIN_EMAILIN_BURAYA"   # <-- setup.sh'daki ile aynı

DEPLOY_DIR="/opt/kernelkompass"

echo "=== Certbot: sertifika alınıyor ==="
docker run --rm \
  -v kernelkompass_certbot_www:/var/www/certbot \
  -v kernelkompass_certbot_certs:/etc/letsencrypt \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  -d "www.$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email

echo ""
echo "Sertifika alındı! Şimdi HTTPS'e geç:"
echo "  bash $DEPLOY_DIR/backend/enable-https.sh"
