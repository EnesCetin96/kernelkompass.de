"""
E-posta gönderme modülü.

Basit tutuldu: stdlib'deki smtplib kullanılıyor, ekstra bir SDK/bağımlılık
gerekmiyor. Herhangi bir SMTP sağlayıcısıyla çalışır (Brevo, Mailgun,
kendi sunucun vb.) — sadece .env'deki SMTP_* değişkenlerini doldurman
yeterli. Önerilen: Brevo (ücretsiz katman: günde 300 e-posta, kredi kartı
istemiyor). Kurulum adımları için EMAIL_SETUP.md'ye bak.

Not: SMTP ayarları boşsa (.env doldurulmadıysa) e-postalar gönderilmez,
bunun yerine konsola/loglara yazdırılır — böylece SMTP kurulmadan da
geliştirme/test yapılabilir (linki logdan kopyalayıp elle deneyebilirsin).
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("kernelkompass.email")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@kernelkompass.de")
FROM_NAME = os.getenv("FROM_NAME", "KernelKompass")

# Doğrulama/şifre sıfırlama linklerinin işaret edeceği adres.
# Deploy sonrası .env'de https://kernelkompass.de/app olarak ayarlanacak.
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")


def _send_raw(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        # SMTP henüz yapılandırılmadı (yerel geliştirme). Linki kaybetmemek
        # için loglara yazdırıyoruz.
        logger.warning(
            "SMTP yapılandırılmadı — e-posta GÖNDERİLMEDİ. "
            "Alıcı: %s | Konu: %s\n--- İçerik ---\n%s",
            to_email, subject, text_body,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, [to_email], msg.as_string())
        return True
    except Exception:
        logger.exception("E-posta gönderilemedi: %s", to_email)
        return False


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    link = f"{APP_BASE_URL}/verify-email.html?token={token}"
    subject = "KernelKompass — e-postanı doğrula"
    text = (
        f"Merhaba {username},\n\n"
        f"KernelKompass hesabını doğrulamak için şu bağlantıya tıkla:\n{link}\n\n"
        f"Bu bağlantı 24 saat geçerlidir. Bu kaydı sen yapmadıysan bu e-postayı yok sayabilirsin."
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
      <h2 style="color:#a8672a;">KernelKompass</h2>
      <p>Merhaba <b>{username}</b>,</p>
      <p>Hesabını doğrulamak için aşağıdaki butona tıkla:</p>
      <p style="text-align:center;margin:28px 0;">
        <a href="{link}" style="background:#e3a94a;color:#161200;padding:12px 24px;
           border-radius:24px;text-decoration:none;font-weight:bold;">E-postamı Doğrula</a>
      </p>
      <p style="color:#888;font-size:13px;">Buton çalışmazsa bu bağlantıyı tarayıcına yapıştır:<br>{link}</p>
      <p style="color:#888;font-size:13px;">Bu bağlantı 24 saat geçerlidir. Bu kaydı sen yapmadıysan bu e-postayı yok sayabilirsin.</p>
    </div>
    """
    return _send_raw(to_email, subject, html, text)


def send_password_reset_email(to_email: str, username: str, token: str) -> bool:
    link = f"{APP_BASE_URL}/reset-password.html?token={token}"
    subject = "KernelKompass — şifre sıfırlama"
    text = (
        f"Merhaba {username},\n\n"
        f"Şifreni sıfırlamak için şu bağlantıya tıkla:\n{link}\n\n"
        f"Bu bağlantı 1 saat geçerlidir. Bu isteği sen yapmadıysan bu e-postayı yok sayabilirsin, "
        f"şifren değişmeyecek."
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;">
      <h2 style="color:#a8672a;">KernelKompass</h2>
      <p>Merhaba <b>{username}</b>,</p>
      <p>Şifreni sıfırlamak için aşağıdaki butona tıkla:</p>
      <p style="text-align:center;margin:28px 0;">
        <a href="{link}" style="background:#e3a94a;color:#161200;padding:12px 24px;
           border-radius:24px;text-decoration:none;font-weight:bold;">Şifremi Sıfırla</a>
      </p>
      <p style="color:#888;font-size:13px;">Buton çalışmazsa bu bağlantıyı tarayıcına yapıştır:<br>{link}</p>
      <p style="color:#888;font-size:13px;">Bu bağlantı 1 saat geçerlidir. Bu isteği sen yapmadıysan bu e-postayı yok sayabilirsin, şifren değişmeyecek.</p>
    </div>
    """
    return _send_raw(to_email, subject, html, text)
