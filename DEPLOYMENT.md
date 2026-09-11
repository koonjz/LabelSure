# LabelSure — Deployment Guide

This document covers everything needed to take LabelSure from a local dev setup to a
live deployed service. It is split into two sections:

- **Part A** — code changes already made for you (reference only)
- **Part B** — manual steps you must do yourself, in the correct order

---

## Part A — What Was Changed in Code

| File | What Changed |
|------|-------------|
| `backend/config.py` | `SECRET_KEY` validation (crashes if missing/weak), `CORS_ORIGINS` env var, rate-limit constants, db pool settings |
| `backend/database.py` | Conditional connection pooling for Postgres vs. SQLite |
| `backend/main.py` | Structured JSON logging, per-IP rate limiting on auth/upload, CORS from env, `/docs` hidden in prod, DB-ping health check |
| `backend/requirements.txt` | Added `gunicorn`, `aiosqlite` |
| `backend/Dockerfile` | Multi-stage build, non-root user, gunicorn entrypoint |
| `docker-compose.yml` | All secrets from `.env`, fails loudly if vars missing |
| `.env.example` | Every variable documented, no real values |
| `.gitignore` | Blocks `.env`, `*.db`, `uploads/`, keystores |
| `frontend/lib/config/app_config.dart` | Release builds assert-crash if `API_BASE_URL` is still the dev default |
| `frontend/android/app/src/main/AndroidManifest.xml` | Cleartext flag removed from base |
| `frontend/android/app/src/debug/AndroidManifest.xml` | Cleartext HTTP added for debug builds only |
| `frontend/android/app/src/release/res/xml/network_security_config.xml` | HTTPS-only for release |
| `frontend/android/app/build.gradle` | Release signing config from `key.properties` or env vars |
| `web_dashboard/vite.config.js` | `VITE_API_URL` env var, production build output |

---

## Part B — Manual Steps

Follow these in order. Each step that is a **hard blocker** for a live demo is
marked 🔴. Steps marked 🟡 can wait until after the demo.

---

### Step 1 — Choose a Hosting Provider 🔴

**Recommendation for a hackathon-stage app: [Railway](https://railway.app)**

**Why Railway:**
- Deploys directly from a GitHub repo with zero config
- Managed PostgreSQL database available as a one-click add-on
- Free tier: $5/month credit — enough for a hackathon demo with low traffic
- Automatic HTTPS on a `*.up.railway.app` subdomain (no Let's Encrypt/Certbot needed)
- Tesseract (apt packages) installable via the `Dockerfile` you already have
- No credit card required for the starter tier

**Alternatives and their trade-offs:**

| Provider | Pros | Cons for this app |
|----------|------|-------------------|
| **Render** | Similar to Railway, free tier exists | Free tier sleeps after 15 min inactivity (bad for demo) |
| **Fly.io** | Fast global edge, persistent volumes | Slightly more complex initial setup |
| **VPS (DigitalOcean/Hetzner)** | Full control, cheap (€5/mo Hetzner) | Manual Nginx/SSL setup, more ops work |
| **AWS/GCP/Azure** | Production-grade | Complex, expensive for small apps, not worth it for hackathon |

**For a real production rollout after the hackathon:** Move to a VPS (Hetzner CX21
at €5/month) or a managed Kubernetes service. Railway becomes expensive at scale.

---

### Step 2 — Set Up Railway (or your chosen host) 🔴

1. Go to [railway.app](https://railway.app) → **Sign in with GitHub**

2. Click **New Project → Deploy from GitHub repo**
   - Connect your GitHub account if prompted
   - Select the `LabelSure` repository
   - Railway will detect the `Dockerfile` in `backend/` automatically

3. **Configure the root directory:**
   In Railway project settings → **Source** → set **Root Directory** to `backend`
   (because the Dockerfile lives at `backend/Dockerfile`)

4. **Add environment variables** (Settings → Variables → click "New Variable" for each):

   ```
   SECRET_KEY          = <generate: python -c "import secrets; print(secrets.token_hex(32))">
   CORS_ORIGINS        = *                        # tighten after dashboard is deployed
   DEBUG               = false
   LOG_FORMAT          = json
   UPLOAD_DIR          = /app/uploads
   MAX_UPLOAD_SIZE_MB  = 20
   WORKERS             = 2
   ```

   > **Do not add `DATABASE_URL` yet** — you'll get it in Step 3.

5. Click **Deploy**. First deploy will take ~10–15 min (PaddleOCR and system deps are large).
   Subsequent deploys are faster (Docker layer cache).

6. Note your app's public URL: `https://labelsure-backend-<hash>.up.railway.app`

---

### Step 3 — Provision PostgreSQL 🔴

**On Railway (simplest):**

1. In your Railway project dashboard → **+ New** → **Database** → **PostgreSQL**

2. Once created, click the database service → **Variables** tab → copy the value of
   `DATABASE_URL` (it looks like `postgresql://user:pass@host.railway.internal:5432/railway`)

3. **Change the scheme to asyncpg:**
   Replace `postgresql://` with `postgresql+asyncpg://`
   Result: `postgresql+asyncpg://user:pass@host.railway.internal:5432/railway`

4. In your backend service → **Variables** → add:
   ```
   DATABASE_URL = postgresql+asyncpg://user:pass@host.railway.internal:5432/railway
   ```

5. Redeploy the backend (or it will restart automatically).

6. **Verify:** Visit `https://your-app.up.railway.app/health` in a browser.
   You should see: `{"status": "ok", "db": "ok", ...}`

> **Alternatively**, [Supabase](https://supabase.com) gives a free managed Postgres with a nice dashboard.
> Use the "Session mode" connection string (port 5432) prefixed with `postgresql+asyncpg://`.

---

### Step 4 — Tesseract and OS Dependencies 🔴

> **Good news: You don't need to do anything extra if using the provided Dockerfile.**

The `backend/Dockerfile` already handles this:

```dockerfile
RUN apt-get install -y tesseract-ocr \
    tesseract-ocr-hin tesseract-ocr-tam tesseract-ocr-tel \
    tesseract-ocr-kan tesseract-ocr-ben ...
```

Railway builds and runs the Docker image, so Tesseract and all Indic language packs
are installed automatically as part of the container build.

**If you are NOT using Docker (bare VPS):**

```bash
# Ubuntu 22.04 / Debian
sudo apt-get update
sudo apt-get install -y \
  tesseract-ocr \
  tesseract-ocr-hin tesseract-ocr-tam tesseract-ocr-tel \
  tesseract-ocr-kan tesseract-ocr-ben \
  libgomp1 libglib2.0-0 libsm6 libxext6 libxrender1 libgl1-mesa-glx

# Verify:
tesseract --version
tesseract --list-langs  # should include hin, tam, tel, kan, ben
```

PaddleOCR's Python models are downloaded automatically on first use (~1.5 GB).
On Railway, add a persistent volume at `/app/.paddleocr` to avoid re-downloading
on every deploy.

---

### Step 5 — Domain and HTTPS 🔴

**Railway subdomain (fastest for hackathon — no action needed):**

Railway automatically gives you an HTTPS URL at `https://<your-app>.up.railway.app`.
This is fully valid TLS, no Let's Encrypt setup needed. Use this for the demo.

**Custom domain (if you want `api.labelsure.app`):**

1. Buy a domain at [Namecheap](https://namecheap.com), [Porkbun](https://porkbun.com),
   or [Cloudflare Registrar](https://cloudflare.com) (~$10–15/year for `.app`).

2. In Railway → your service → **Settings** → **Domains** → **Add Custom Domain**

3. Railway gives you a CNAME record to add in your DNS provider:
   ```
   Type: CNAME
   Name: api
   Value: <railway-provided-target>
   ```

4. Railway provisions the TLS certificate automatically via Let's Encrypt.
   No Certbot needed.

**If you're on a bare VPS:**

Use Nginx as a reverse proxy + Certbot:

```bash
sudo apt-get install nginx certbot python3-certbot-nginx
sudo certbot --nginx -d api.labelsure.app
```

Certbot auto-renews certificates. Point Nginx to `localhost:8000` (where gunicorn runs).

---

### Step 6 — Deploy the Web Dashboard 🔴

The web dashboard is a static React/Vite app — host it on Netlify or Vercel (both free).

**Option A: Netlify (recommended, simplest)**

1. Go to [netlify.com](https://netlify.com) → **Add new site → Import from Git**

2. Select your GitHub repo → set:
   - **Base directory:** `web_dashboard`
   - **Build command:** `npm run build`
   - **Publish directory:** `web_dashboard/dist`

3. Add an environment variable in Netlify (Site settings → Environment variables):
   ```
   VITE_API_URL = https://your-backend.up.railway.app
   ```

4. Deploy. You'll get a URL like `https://labelsure-dashboard.netlify.app`.

5. **Update CORS on the backend:** In Railway → backend Variables:
   ```
   CORS_ORIGINS = https://labelsure-dashboard.netlify.app
   ```
   If you have both Netlify and the Railway subdomain to allow:
   ```
   CORS_ORIGINS = https://labelsure-dashboard.netlify.app,https://labelsure.netlify.app
   ```
   Redeploy the backend.

**Option B: Vercel**

1. [vercel.com](https://vercel.com) → **New Project → Import Git Repository**
2. Set **Root Directory** to `web_dashboard`
3. Add env var `VITE_API_URL=https://your-backend.up.railway.app`
4. Deploy — same result.

**Option C: Serve from the same backend (simplest, no CORS needed)**

Copy the built `dist/` into the backend and serve it with FastAPI's StaticFiles.
Then `CORS_ORIGINS` doesn't matter for the dashboard (same origin).

```bash
cd web_dashboard
VITE_API_URL='' npm run build     # empty = uses relative /auth, /scans paths
cp -r dist/ ../backend/static/dashboard/
```

In `backend/main.py`, add:
```python
from fastapi.responses import FileResponse
app.mount("/dashboard", StaticFiles(directory="static/dashboard", html=True), name="dashboard")
```

This is slightly simpler for a hackathon demo but mixes concerns.

---

### Step 7 — Android Signing Key 🟡

> 🟡 **Not a hard blocker for sideloading** — debug-signed APKs work fine for direct install.
> **Required** if you ever submit to the Play Store.

**Generate a keystore:**

```bash
# Run this on your local machine (not the server)
keytool -genkey -v \
  -keystore labelsure-release.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias labelsure

# You'll be prompted for:
#   - Keystore password (remember this — you can never recover it)
#   - Key password (can be same as keystore password)
#   - Your name / org / city / country (can be generic for a hackathon)
```

**Wire it up:**

1. Copy `frontend/android/key.properties.example` → `frontend/android/key.properties`

2. Fill in `key.properties`:
   ```
   storePassword=YOUR_KEYSTORE_PASSWORD
   keyPassword=YOUR_KEY_PASSWORD
   keyAlias=labelsure
   storeFile=../../labelsure-release.jks
   ```
   (Path is relative to `android/app/build.gradle` — adjust if you put the jks elsewhere)

3. **Back up the `.jks` file** — losing it means you can never update the app on Play Store.
   Store it in a password manager (1Password, Bitwarden) or encrypted cloud storage.

4. Confirm `*.jks` and `key.properties` are in `.gitignore` (they already are).

---

### Step 8 — Build the Release APK 🔴

```bash
cd frontend

# Build signed release APK (for direct sideloading / hackathon demo)
flutter build apk --release \
  --dart-define=API_BASE_URL=https://your-backend.up.railway.app

# APK location:
# build/app/outputs/flutter-apk/app-release.apk

# OR build an App Bundle (required for Play Store, not needed for sideloading)
flutter build appbundle --release \
  --dart-define=API_BASE_URL=https://your-backend.up.railway.app
```

**If you haven't set up `key.properties`** (quickest for demo):

The build will warn you and fall back to the debug keystore, which is fine for direct
APK distribution. The warning looks like:
```
[LabelSure] WARNING: No key.properties or KEYSTORE_FILE env var found.
  Release build will be signed with the DEBUG keystore.
```

---

### Step 9 — Getting the APK Onto a Judge's Phone 🔴

For a **hackathon demo** you do NOT need the Play Store. Two options:

**Option A: ADB install (requires USB cable)**
```bash
# Connect the judge's phone via USB with USB Debugging enabled
adb install build/app/outputs/flutter-apk/app-release.apk
```

**Option B: Direct APK download (no cable needed — better for demos)**

1. Upload the APK to any file host:
   - GitHub Releases (free, permanent): create a release on your repo and attach the APK
   - Google Drive shared link
   - Netlify drop (drag-and-drop): [netlify.com/drop](https://app.netlify.com/drop)

2. Create a QR code pointing to the direct download link:
   - [qr-code-generator.com](https://www.qr-code-generator.com) (free)
   - Or use `qrencode` CLI: `qrencode -o demo.png "https://your-apk-link"`

3. The judge scans the QR code, downloads the APK, taps **Install**.

4. **Android will warn "Install from unknown source"** — the judge needs to:
   - Go to **Settings → Apps → (their browser) → Install unknown apps → Allow**
   - Then tap the downloaded APK

> 💡 **Prep tip:** Pre-install the app on 2–3 demo phones before the hackathon so
> you don't waste time troubleshooting "unknown source" settings during the demo.

---

### Step 10 — Expected Costs

**At hackathon/demo scale (< 100 scans/day, 1–5 concurrent users):**

| Service | Provider | Cost/month |
|---------|----------|-----------|
| Backend hosting | Railway starter | ~$0–5 (within free credit) |
| PostgreSQL | Railway managed | Included in starter |
| Web dashboard | Netlify / Vercel | $0 (free tier) |
| Domain (optional) | Porkbun | ~$1/month (billed annually) |
| Uploaded images (local disk) | Railway volume | Included |
| **Total** | | **~$0–6/month** |

**At real production scale (1,000+ scans/day):**

| Service | Provider | Cost/month |
|---------|----------|-----------|
| Backend (2 workers) | Railway Pro or Render | ~$20–40 |
| PostgreSQL (managed) | Railway / Supabase Pro | ~$15–25 |
| Image storage | AWS S3 or Cloudflare R2 | ~$1–5 (20 GB) |
| CDN (images) | Cloudflare free tier | $0 |
| Domain + SSL | Any registrar | ~$1/month |
| **Total** | | **~$37–71/month** |

---

### Step 11 — Backups and Image Storage 🟡

> 🟡 **Can wait until after the demo.**

**Database backups:**

Railway's managed PostgreSQL has automatic daily backups with 7-day retention on
the paid plan. For the free tier, set up a manual backup:

```bash
# Run this daily via a cron job or Railway Cron service
pg_dump $DATABASE_URL | gzip > backup-$(date +%Y%m%d).sql.gz
# Upload to Backblaze B2 or S3 (~$0.006/GB/month)
```

**Uploaded label images:**

Current setup: images are stored on the container's local filesystem (`/app/uploads`),
mounted as a Railway volume. This works for demo scale.

**For production scale, move images to object storage:**

- [Cloudflare R2](https://developers.cloudflare.com/r2/): $0.015/GB/month, **no egress fees**
  (best choice — free egress is unique to R2)
- [AWS S3](https://aws.amazon.com/s3/): $0.023/GB/month + egress fees
- [Backblaze B2](https://www.backblaze.com/b2/): $0.006/GB/month + egress fees

**Decision for hackathon:** Keep images on disk (current setup). If the app goes
to production, swap `settings.upload_dir` for an S3/R2 client (e.g. `boto3` or
Cloudflare's S3-compatible API). You can choose to only store extracted data
(OCR text, field values, rule results) and delete raw images after 30 days to
keep storage costs near zero.

---

## Quick-Start Checklist

Use this as your run-of-show for the day before the demo:

```
□ Step 1: Railway account created, GitHub repo connected
□ Step 2: Backend deployed, public URL noted (https://xxx.up.railway.app)
□ Step 3: PostgreSQL add-on created, DATABASE_URL set, /health returns {"db":"ok"}
□ Step 4: (Automatic via Dockerfile — verify by uploading a test image)
□ Step 5: HTTPS working on Railway subdomain (no action needed)
□ Step 6: Web dashboard deployed on Netlify, VITE_API_URL set, CORS updated on backend
□ Step 7: (Optional — skip for demo, use debug keystore)
□ Step 8: Release APK built with --dart-define=API_BASE_URL=https://xxx.up.railway.app
□ Step 9: APK uploaded to GitHub Releases, QR code generated
□ Pre-install APK on demo devices, test end-to-end scan flow
□ Create a demo officer account via POST /auth/register or the web dashboard
```

---

## Environment Variable Quick Reference

| Variable | Required | Example | What it does |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ prod | `postgresql+asyncpg://user:pw@host:5432/db` | Async DB connection |
| `SECRET_KEY` | ✅ always | `7f3a1b9e...` (32+ hex chars) | JWT signing key |
| `CORS_ORIGINS` | ✅ prod | `https://dashboard.labelsure.app` | Allowed frontend origins |
| `DEBUG` | ✅ | `false` | Hides /docs, enables query echo |
| `LOG_FORMAT` | ✅ prod | `json` | Structured logging for log aggregators |
| `WORKERS` | ✅ prod | `2` | Gunicorn worker processes |
| `UPLOAD_DIR` | ✅ | `/app/uploads` | Where label images are saved |
| `MAX_UPLOAD_SIZE_MB` | ✅ | `20` | Max accepted image size |
| `CORS_ORIGINS` | ✅ prod | `https://dashboard.labelsure.app` | CORS allowlist |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | optional | `1440` | JWT expiry (default 24h) |
| `RATE_LIMIT_AUTH_RPM` | optional | `20` | Auth rate limit per IP/min |
| `RATE_LIMIT_UPLOAD_RPM` | optional | `30` | Upload rate limit per IP/min |
| `OCR_CONFIDENCE_THRESHOLD` | optional | `0.70` | Below this → NEEDS_REVIEW |
| `POSTGRES_PASSWORD` | docker-compose | `strong_random_pw` | DB password for compose `db` service |
| `POSTGRES_USER` | docker-compose | `labelsure` | DB user for compose `db` service |
| `POSTGRES_DB` | docker-compose | `labelsure` | DB name for compose `db` service |
