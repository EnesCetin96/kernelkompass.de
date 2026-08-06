#!/bin/bash
# nginx'i HTTPS moduna geçir
# Önkoşul: get-cert.sh başarıyla tamamlandı
set -e

DEPLOY_DIR="/opt/kernelkompass"

echo "=== nginx HTTPS moduna geçiriliyor ==="
cp "$DEPLOY_DIR/backend/nginx/nginx-https.conf" \
   "$DEPLOY_DIR/backend/nginx/nginx.conf"

cd "$DEPLOY_DIR/backend"
docker compose exec nginx nginx -s reload

echo ""
echo "HTTPS aktif! Test et:"
echo "  curl https://kernelkompass.de/api/health"
echo "  curl https://kernelkompass.de"
echo ""
echo "Otomatik sertifika yenileme için cron ekle:"
echo "  crontab -e"
echo "  # Şu satırı ekle:"
echo "  0 3 * * * docker run --rm -v kernelkompass_certbot_www:/var/www/certbot -v kernelkompass_certbot_certs:/etc/letsencrypt certbot/certbot renew --webroot -w /var/www/certbot && docker compose -f /opt/kernelkompass/backend/docker-compose.yml exec nginx nginx -s reload"
