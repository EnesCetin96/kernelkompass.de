# E-posta Kurulumu (Brevo ile)

KernelKompass, hesap doğrulama ve şifre sıfırlama e-postaları için bir
SMTP sağlayıcısına ihtiyaç duyar. **Brevo** (eski adıyla Sendinblue)
öneriliyor: ücretsiz katmanında günde 300 e-posta (aylık ~9000) hakkı var,
kredi kartı istemiyor, düz SMTP ile çalışıyor.

Not: Kod herhangi bir SMTP sağlayıcısıyla çalışır (Mailgun, kendi
sunucun, vb.) — sadece aşağıdaki adımları o sağlayıcının kendi SMTP
bilgileriyle uyarlaman yeterli.

## 1) Brevo hesabı aç
1. https://www.brevo.com adresine git, "Sign up free" ile ücretsiz hesap aç.
2. E-posta adresini doğrula (Brevo sana bir doğrulama e-postası gönderecek —
   evet, kendi e-posta doğrulama sistemimizi kurarken önce başka birinin
   e-posta doğrulamasından geçiyoruz, biraz ironik ama gerekli).

## 2) SMTP bilgilerini al
1. Brevo panelinde sağ üstten profiline tıkla → **SMTP & API** sekmesine git.
2. **SMTP** sekmesinde şu bilgileri göreceksin:
   - SMTP sunucusu: `smtp-relay.brevo.com`
   - Port: `587`
   - Giriş (login): genelde Brevo'ya kayıt olduğun e-posta adresin
   - **SMTP anahtarı (key)**: "Generate a new SMTP key" ile yeni bir anahtar
     üret — bu, `.env` dosyandaki `SMTP_PASSWORD` olacak (senin Brevo
     şifren DEĞİL, ayrı bir anahtar).

## 3) Gönderen adresini doğrula (sender verification)
Brevo, spam'i önlemek için hangi adresten e-posta gönderdiğini bilmek ister.
İki seçenek var:

**Seçenek A — hızlı başlangıç (domain doğrulamadan):**
Brevo panelinde **Senders & IP → Senders** kısmından tek bir e-posta
adresi ekleyip doğrulayabilirsin (ör. kendi Gmail adresin). Bu durumda
`.env`'deki `FROM_EMAIL` bu adres olur — `no-reply@kernelkompass.de`
değil, doğruladığın gerçek adres.

**Seçenek B — profesyonel (domain doğrulamayla, kernelkompass.de barındırma
netleşince):**
1. Brevo panelinde **Senders & IP → Domains** kısmından `kernelkompass.de`
   domainini ekle.
2. Brevo sana birkaç DNS kaydı verecek (SPF, DKIM — genelde TXT/CNAME
   kayıtları).
3. Bu kayıtları INWX panelinde (domainin nerede kayıtlıysa orada) DNS
   ayarlarına ekle.
4. Birkaç saat içinde Brevo domaini "doğrulandı" olarak işaretleyecek.
5. Bundan sonra `FROM_EMAIL=no-reply@kernelkompass.de` gibi profesyonel
   bir adres kullanabilirsin.

Şimdilik (barındırma netleşmeden) **Seçenek A** ile başlaman yeterli;
domain doğrulaması deploy aşamasında Seçenek B'ye geçilebilir.

## 4) `.env` dosyasını doldur
```
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=brevo-hesabina-kayitli-eposta@ornek.com
SMTP_PASSWORD=brevo-panelinden-uretilen-smtp-anahtari
FROM_EMAIL=dogruladigin-gonderen-adresi@ornek.com
FROM_NAME=KernelKompass
APP_BASE_URL=http://localhost:8080
```

`APP_BASE_URL`, doğrulama/şifre sıfırlama e-postalarındaki linklerin
işaret edeceği adres — webapp'i nerede test ediyorsan (yerelde
`python3 -m http.server` ile 8080 portunda vb.) ona göre ayarla. Deploy
sonrası gerçek adres (`https://kernelkompass.de/app` gibi) olacak.

## 5) Test et
Backend'i başlat (`docker compose up -d db backend`), sonra webapp'ten
bir hesap kaydı yap. Brevo panelinde **Statistics → Email** kısmından
e-postanın gittiğini görebilirsin. Gelen kutusuna (ve spam klasörüne!)
bakmayı unutma.

## SMTP boş bırakılırsa ne olur?
`.env`'de `SMTP_USER`/`SMTP_PASSWORD` boşsa, backend e-postayı GÖNDERMEZ —
bunun yerine doğrulama/sıfırlama linkini backend loglarına yazdırır
(`docker compose logs backend` ile görebilirsin). Bu, SMTP kurmadan önce
kayıt/giriş akışını test etmek için kullanışlıdır.
