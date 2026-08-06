#!/bin/bash
# KernelKompass — EC2 ilk kurulum scripti
# Çalıştır: bash setup.sh
set -e

DOMAIN="kernelkompass.de"
EMAIL="SENIN_EMAILIN_BURAYA"   # <-- değiştir (certbot için)
DEPLOY_DIR="/opt/kernelkompass"

echo "=== [1/6] Sistem güncelleniyor ==="
apt-get update -q
apt-get upgrade -y -q

echo "=== [2/6] UFW güvenlik duvarı ==="
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable

echo "=== [3/6] Docker kuruluyor ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
else
  echo "Docker zaten kurulu, atlanıyor."
fi

echo "=== [4/6] Dosyalar kopyalanıyor ==="
mkdir -p "$DEPLOY_DIR"
# Bu script backend/ klasörünün içinden çalışıyor.
# Üst dizindeki webapp/ klasörü de buraya kopyalanıyor.
cp -r . "$DEPLOY_DIR/backend"
if [ -d "../webapp" ]; then
  cp -r ../webapp "$DEPLOY_DIR/webapp"
  echo "webapp kopyalandı."
else
  echo "UYARI: ../webapp bulunamadı, webapp dosyalarını manuel kopyala."
fi

echo "=== [5/6] webapp Docker volume'üne yükleniyor ==="
# webapp_static volume'ü oluştur ve webapp dosyalarını içine kopyala
docker volume create kernelkompass_webapp_static 2>/dev/null || true
docker run --rm \
  -v kernelkompass_webapp_static:/target \
  -v "$DEPLOY_DIR/webapp":/source:ro \
  alpine sh -c "cp -r /source/. /target/"
echo "webapp volume'üne yüklendi."

echo "=== [6/6] .env dosyası ==="
cd "$DEPLOY_DIR/backend"
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo ">>> .env dosyası oluşturuldu. Şimdi nano .env ile doldur:"
  echo "    - POSTGRES_PASSWORD: güçlü bir şifre"
  echo "    - SECRET_KEY: openssl rand -hex 32"
  echo "    (Sonra bu scriptin devamındaki adımlara geç)"
  echo ""
else
  echo ".env zaten var, atlanıyor."
fi

echo ""
echo "========================================="
echo "  Kurulum tamamlandı!"
echo "========================================="
echo ""
echo "Sıradaki adımlar:"
echo "  1. nano $DEPLOY_DIR/backend/.env  (POSTGRES_PASSWORD ve SECRET_KEY doldur)"
echo "  2. cd $DEPLOY_DIR/backend && docker compose up -d --build"
echo "  3. curl http://$DOMAIN/api/health  (DNS yayıldıktan sonra)"
echo "  4. Sertifika al: bash $DEPLOY_DIR/backend/get-cert.sh"
echo "  5. HTTPS'e geç: bash $DEPLOY_DIR/backend/enable-https.sh"
echo ""
