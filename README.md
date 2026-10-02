# KernelKompass

**A free, multilingual, interactive Linux & DevOps learning platform.**
🌐 **Live:** [kernelkompass.de](https://kernelkompass.de)
· **Open the app directly:** [kernelkompass.de/webapp](https://kernelkompass.de/webapp/)

> **Status (October 2026):** the original production deployment on AWS EC2
> (August–October 2026) has been retired to save costs. `kernelkompass.de`
> now serves a **static demo from GitHub Pages**: the full workbook,
> terminal simulator, and exam system work without logging in, and notes and
> progress are kept in your browser. Accounts, cross-device sync, and comments
> need the backend, which is still in this repo and can be redeployed any time
> (see "Production deployment" below).

KernelKompass teaches Linux and DevOps fundamentals through a browser-based,
hands-on workbook: a simulated bash terminal, a virtual file manager, guided
exercises, and a full exam system — all available in **English, Turkish, and
German**. It's built for absolute beginners, including high school students
and Informatik students in Germany, with no local setup required.

---

## ✨ Features

- **Simulated bash terminal** — a JavaScript-based shell engine that
  supports real commands (`cd`, `ls`, `grep`, `chmod`, `crontab`, etc.)
  against a virtual filesystem, with realistic error handling and no
  actual system access required.
- **11 structured sections** (9 core parts + a Crontab appendix), each
  combining explanations, live terminal practice, and a virtual file
  manager panel.
- **Full exam system** — 100 multiple-choice questions and 50 scenario-based
  tasks, all fully localized in EN/TR/DE.
- **Trilingual by design** — English content is always shown; Turkish and
  German act as a toggleable explanation/commentary layer alongside it.
- **Accounts & sync** *(backend required — off in the static demo)* —
  registration, email verification, password reset, and per-user
  progress/notes stored server-side.
- **Comment system with admin moderation** *(backend required — off in the
  static demo)* — logged-in users can leave comments; an admin approval step
  keeps the workbook's public pages clean.
- **Demo mode** — with no backend configured (`KK_API_BASE = null` in
  `config.js`) the app opens without a login and stores everything in
  `localStorage`, so it can be hosted on any static host.
- **Installable PWA** — works offline after the first load via a service
  worker, and can be added to a phone/tablet home screen like a native app.

---

## 🏗️ Architecture

```
┌─────────────────┐        ┌──────────────────────┐
│  website/        │        │  webapp/              │
│  Landing page     │        │  The learning app     │
│  (EN/TR/DE)        │        │  (PWA, bash terminal, │
│                    │        │   exams, accounts)    │
└─────────┬─────────┘        └──────────┬───────────┘
          │                              │
          └──────────────┬───────────────┘
                          │
                 ┌────────▼─────────┐
                 │   nginx (alpine)  │  reverse proxy + static files
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │  FastAPI backend  │  auth, sync, comments, ads
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │  PostgreSQL 16    │
                 └───────────────────┘
```

In production (August–October 2026) all services ran as Docker Compose
containers on a single AWS EC2 instance (Frankfurt, `eu-central-1`, `t3.micro`,
Ubuntu 24.04), sitting behind Cloudflare (DNS + Flexible SSL). That instance has
since been terminated; the current public demo serves only the two static
frontends (`website/` and `webapp/`) from GitHub Pages.

### Tech stack

| Layer      | Technology                                              |
|------------|----------------------------------------------------------|
| Frontend   | Vanilla HTML/CSS/JavaScript PWA (no framework, no build step) |
| Backend    | FastAPI (Python), SQLAlchemy                             |
| Database   | PostgreSQL 16                                             |
| Email      | Brevo SMTP (verification & password reset)                |
| Web server | nginx (reverse proxy + static file serving)                |
| Deployment | Docker Compose on AWS EC2 (Ubuntu 24.04 LTS)               |
| TLS/DNS    | Cloudflare (Flexible SSL), domain via INWX                 |
| Testing    | Playwright (end-to-end smoke tests)                        |

---

## 📁 Repository layout

```
webapp/                 The learning platform (PWA)
  index.html             Main app shell (nav, terminal engine, UI)
  sections/               Lazily-loaded section content (p0–p9, a2–a25, exams)
  exam-data-*.js           Multiple-choice question banks (modularized)
  sw.js                    Service worker (offline caching)
  manifest.json             PWA manifest
  verify-email.html          Email verification landing page
  reset-password.html         Password reset landing page
  impressum.html               Legal notice (§5 DDG)

website/                Marketing/landing page (EN/TR/DE)
  index.html

backend/                FastAPI application
  app/
    main.py               App entrypoint
    models.py              SQLAlchemy models
    schemas.py               Pydantic schemas
    auth.py                    Auth helpers (hashing, JWT)
    email_utils.py               Brevo SMTP integration
    routers/                       auth, data, comments, ads
  docker-compose.yml         Service definitions (db, backend, nginx)
  nginx/nginx.conf             Reverse proxy config
  requirements.txt              Python dependencies
  Dockerfile

config.js                Single shared `window.KK_API_BASE` definition,
                           loaded by every HTML entry point to avoid
                           duplicating the API base URL.

kk-e2e-test.js           Playwright smoke test (login/register, section
                           navigation, file manager, terminal, exam flow).
                           Run with:
                           npm install -D playwright && npx playwright install chromium
                           node kk-e2e-test.js login <username> <password>

LICENSE-CODE.md / LICENSE-CONTENT.md   See Licensing below.
```

---

## 🚀 Local development

The frontend is static and framework-free — you can open `webapp/index.html`
directly, or serve it with any static file server. For full functionality
(accounts, sync, comments) you'll also need the backend running.

```bash
# Backend
cd backend
docker compose up -d --build

# Frontend — serve statically, e.g.
cd webapp
python3 -m http.server 8080
```

Set `window.KK_API_BASE` in `config.js` to point at your backend
(`http://localhost:8000` for local development). Leave it as `null` to run in
demo mode with no backend at all.

## ☁️ Production deployment

> Not currently deployed — the steps below are how the stack ran on EC2 and
> how to bring it back. After deploying, set `window.KK_API_BASE` in
> `config.js` to the backend's public URL.

The production stack runs as three Docker Compose services (PostgreSQL,
FastAPI/uvicorn, nginx:alpine) on a single EC2 instance:

```bash
docker compose down
docker compose up -d --build
docker compose logs backend --tail 30   # verify clean startup
docker compose ps                        # all three containers should be Up
```

nginx serves `website/` at `/`, `webapp/` at `/webapp/`, and reverse-proxies
`/api/` to the FastAPI backend. TLS is terminated by Cloudflare (Flexible
SSL) — the EC2 nginx instance only needs to serve plain HTTP.

> After changing any file the service worker caches (`webapp/sw.js`'s
> `ASSETS` list, most notably `index.html`), bump `CACHE_NAME` in `sw.js`
> and redeploy it — otherwise browsers keep serving a stale cached version
> even though the server has the latest file.

---

## 📜 Licensing

KernelKompass uses a two-license approach:

- **Code** — [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)
  (see `LICENSE-CODE.md`)
- **Learning content** (section text, explanations, exercises, exam
  questions) — [Creative Commons BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)
  (see `LICENSE-CONTENT.md`)

In short: free to use and learn from, not for commercial use, and content
may not be redistributed in modified form.

---

## 🙋 About

KernelKompass is built and maintained by **Muhammed Enes Çetin** as part of
a DevOps learning journey (Clarusway AWS + DevOps Bootcamp) and as a free
resource for German high school and Informatik students starting out with
Linux.
