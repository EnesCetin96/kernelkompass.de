# Backend'i VPS'e Kurma Rehberi

Bu rehber, `index.html`'in GitHub Pages'te kalmaya devam ettiğini, sadece
üyelik/senkron API'sinin bu backend üzerinden çalışacağını varsayar.

## 0) VPS satın al
- Hetzner Cloud (CX22, ~4-5€/ay) veya DigitalOcean benzer bir "Droplet" yeterli.
- İşletim sistemi: **Ubuntu 24.04 LTS**.
- Bir domain adın yoksa ücretsiz bir alt-domain servisi (ör. DuckDNS) da kullanabilirsin,
  ama gerçek bir domain (yıllık ~5-10$) daha profesyonel durur.

## 1) Sunucuya bağlan ve temel güvenlik
```bash
ssh root@SUNUCU_IP

# Sistem güncelle
apt update && apt upgrade -y

# Basit güvenlik duvarı: sadece SSH, HTTP, HTTPS açık
apt install -y ufw
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

## 2) Docker kur
```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

## 3) Domain'i sunucuya yönlendir
Domain sağlayıcında (Namecheap, GoDaddy vb.) bir **A kaydı** oluştur:
```
Tip: A
Host: api  (yani api.senindomainin.com)
Değer: SUNUCU_IP
```
DNS yayılması birkaç dakika-birkaç saat sürebilir. `ping api.senindomainin.com`
ile sunucunun IP'sini döndürdüğünü doğrula.

## 4) Proje dosyalarını sunucuya yükle
Kendi bilgisayarından:
```bash
scp -r backend root@SUNUCU_IP:/root/workbook-backend
```

## 5) Ortam değişkenlerini ayarla
```bash
ssh root@SUNUCU_IP
cd /root/workbook-backend
cp .env.example .env
nano .env
```
- `POSTGRES_PASSWORD`: güçlü bir şifre gir.
- `SECRET_KEY`: `openssl rand -hex 32` komutuyla üret, çıktıyı yapıştır.
- `CORS_ORIGINS`: senin GitHub Pages adresin (ör. `https://kullaniciadin.github.io`).

`nginx/nginx.conf` dosyasında `DOMAININ_BURAYA.com` yazan yeri
`api.senindomainin.com` ile değiştir.

## 6) İlk çalıştırma (HTTPS'siz, sertifika almak için)
```bash
docker compose up -d --build
docker compose ps   # her şey "healthy/running" olmalı
```
Test et: `curl http://api.senindomainin.com/api/health` → `{"status":"ok"}` dönmeli.

## 7) HTTPS sertifikası al (Let's Encrypt / Certbot)
```bash
docker run -it --rm \
  -v $(pwd)/certbot-www:/var/www/certbot \
  -v certbot_certs:/etc/letsencrypt \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d api.senindomainin.com \
  --email SENIN_EMAILIN --agree-tos --no-eff-email
```
Not: compose'daki volume adları (`certbot_www`, `certbot_certs`) ile burada
kullandığın volume'lerin eşleştiğinden emin ol — gerekirse
`docker compose config --volumes` ile kontrol et ve komuttaki mount noktalarını
projendeki gerçek volume adlarına göre düzelt.

## 8) nginx'i HTTPS'e geçir
`nginx/nginx.conf` dosyasının içeriğini şununla değiştir:
```nginx
server {
    listen 80;
    server_name api.senindomainin.com;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    server_name api.senindomainin.com;

    ssl_certificate     /etc/letsencrypt/live/api.senindomainin.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.senindomainin.com/privkey.pem;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Sonra:
```bash
docker compose restart nginx
```

## 9) Sertifika otomatik yenileme
Let's Encrypt sertifikaları 90 günde bir yenilenmeli. Basit bir cron:
```bash
crontab -e
# şu satırı ekle:
0 3 * * * docker run --rm -v certbot_www:/var/www/certbot -v certbot_certs:/etc/letsencrypt certbot/certbot renew --webroot -w /var/www/certbot && docker restart workbook-backend-nginx-1
```

## 10) Sağlık kontrolü ve loglar
```bash
docker compose logs -f backend
docker compose logs -f nginx
```

## Güncelleme yapmak istediğinde
```bash
cd /root/workbook-backend
git pull   # ya da yeniden scp
docker compose up -d --build
```

---
Bu noktadan sonra API adresin: `https://api.senindomainin.com/api/...`
Bir sonraki adım: `index.html` içindeki JS'i bu API'ye bağlamak
(kayıt ol / giriş yap ekranı + notlar/terminal/ilerleme senkronu).
Bunu istersen ayrı bir mesajda, mevcut arayüzü bozmadan entegre edelim.
