# Oracle Cloud Always Free — Sunucu Kurulumu

Bu adımları bitirdikten sonra ana `DEPLOY.md` dosyasındaki 4. adımdan
(Proje dosyalarını sunucuya yükle) devam edeceksin — geri kalan her şey aynı.

## 1) Hesap oluştur
1. https://www.oracle.com/cloud/free/ adresinden ücretsiz hesap aç.
2. Kredi kartı doğrulama isteyecek — bu sadece kimlik doğrulama, Always Free
   kaynaklarını kullandığın sürece ücret kesilmez.
3. Bölge (region) seçerken Frankfurt (eu-frankfurt-1) senin için en düşük
   gecikmeli seçenek — ama "kapasite yok" hatası alırsan Amsterdam
   (eu-amsterdam-1) gibi komşu bir Avrupa bölgesini dene.

## 2) Sanal makine (instance) oluştur
1. Console'da sol üstten **Compute → Instances → Create Instance**.
2. **Image and shape** kısmında "Edit" e tıkla:
   - Image: **Ubuntu 24.04**
   - Shape: **VM.Standard.A1.Flex** seç, **2 OCPU / 12 GB RAM** ayarla
     (2026 ortası itibarıyla ücretsiz hesaplar için üst sınır bu — bizim
     proje için fazlasıyla yeterli).
3. **Add SSH keys**: "Generate a key pair for me" seç, **private key'i indir**
   ve güvenli bir yere kaydet (bir daha gösterilmiyor).
4. "Create" de, birkaç dakika içinde instance "Running" durumuna geçer.
5. Instance detay sayfasından **Public IP adresini** not al.

Eğer "Out of host capacity" hatası alırsan: birkaç dakika/saat sonra tekrar
dene, ya da farklı bir Availability Domain (AD-1/AD-2/AD-3) seç. Bu, Oracle'ın
ücretsiz ARM kapasitesinin bazı bölgelerde/saatlerde dolu olmasından kaynaklanır,
hesabınla ilgili bir sorun değildir.

## 3) SSH ile bağlan
```bash
chmod 600 indirdigin-private-key.key
ssh -i indirdigin-private-key.key ubuntu@PUBLIC_IP
```
(Not: Oracle'ın Ubuntu image'ında kullanıcı adı `root` değil, **`ubuntu`**.)

## 4) Oracle'ın kendi güvenlik duvarını aç (EN SIK ATLANAN ADIM)
Ana `DEPLOY.md`'deki `ufw` ayarı **yetmez** — Oracle'ın VCN (Virtual Cloud
Network) seviyesinde ayrı bir güvenlik katmanı var, bunu da açman gerekiyor:

1. Console'da instance sayfasına git → **Subnet** linkine tıkla.
2. **Security Lists** → default security list'e tıkla.
3. **Add Ingress Rules** ile şunları ekle:
   - Source CIDR: `0.0.0.0/0`, IP Protocol: TCP, Destination Port: **80**
   - Source CIDR: `0.0.0.0/0`, IP Protocol: TCP, Destination Port: **443**
4. Sunucu içinde de `ufw` ile aynı portları aç (DEPLOY.md'deki gibi).

İki katman da açık olmazsa (Oracle paneli + ufw), dışarıdan siteye
ulaşamazsın — en yaygın "neden çalışmıyor" sebebi budur.

## 5) Statik IP (opsiyonel ama önerilir)
Instance'ın Public IP'si varsayılan olarak "ephemeral" (geçici) — sunucuyu
durdurup tekrar başlatırsan değişebilir. Bunu sabitlemek için:
Console → Networking → **Reserved Public IPs** → yeni bir reserved IP oluştur
ve instance'ına ata. Böylece domain'ini bir kere ayarlayıp unutabilirsin.

---
Buradan sonra ana `DEPLOY.md` dosyasındaki **4. adım**dan (dosyaları yükle)
devam et — geri kalan Docker/nginx/certbot süreci birebir aynı.
