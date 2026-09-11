# LabelSure

**AI-powered compliance scanner for India's Legal Metrology (Packaged Commodities) Rules, 2011**

LabelSure helps Legal Metrology enforcement officers, manufacturers, and e-commerce sellers instantly verify whether a packaged-product label complies with the PCR 2011 Rules — using OCR, computer vision, and a standalone rules engine.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Setup — Backend](#setup--backend)
3. [Setup — Flutter Mobile App](#setup--flutter-mobile-app)
4. [Setup — Officer Web Dashboard](#setup--officer-web-dashboard)
5. [Running with Docker](#running-with-docker)
6. [Running Tests](#running-tests)
7. [Sample Label Images](#sample-label-images)
8. [Rules Encoded](#rules-encoded)
9. [API Reference](#api-reference)
10. [Known Limitations](#known-limitations)
11. [Project Structure](#project-structure)

---

## Architecture

```
Flutter Mobile App (Android/iOS)        React Officer Web Dashboard
         │                                         │
         └───────────────┬─────────────────────────┘
                         │  REST API (HTTP/JSON)
                ┌────────▼────────┐
                │  FastAPI Backend │
                │  (Python 3.11)   │
                └────────┬─────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
   ┌──────▼──┐   ┌───────▼──┐  ┌──────▼──┐
   │  OCR    │   │CV Geometry│  │  NLP    │
   │ Engine  │   │  Engine   │  │ Lang ID │
   │PaddleOCR│   │  OpenCV   │  │langdetect│
   └──────┬──┘   └───────┬──┘  └──────┬──┘
          └──────────────┼──────────────┘
                         │
                ┌────────▼────────┐
                │  Rules Engine   │
                │  (standalone,   │
                │   versioned)    │
                └────────┬─────────┘
                         │
                ┌────────▼────────┐
                │   PostgreSQL    │
                │ (scans, fields, │
                │  violations,    │
                │   audit log)    │
                └─────────────────┘
```

---

## Setup — Backend

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or use Docker — see below)
- Tesseract OCR (for fallback OCR)

### 1. Install Tesseract

**Windows:**
```powershell
# Download installer from https://github.com/UB-Mannheim/tesseract/wiki
# Install and add to PATH
# Also download Hindi/Tamil/Telugu language packs
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam tesseract-ocr-tel tesseract-ocr-kan tesseract-ocr-ben
```

### 2. Create virtual environment & install dependencies

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

> **Note:** PaddleOCR requires ~1.5 GB of disk space for models. On first run, models are downloaded automatically. If PaddleOCR installation fails, Tesseract will be used as fallback.

### 3. Configure environment

```bash
# From project root:
cp .env.example .env
# Edit .env and set your DATABASE_URL and SECRET_KEY
```

### 4. Start PostgreSQL

Either use Docker:
```bash
docker run -d --name labelsure_pg \
  -e POSTGRES_DB=labelsure \
  -e POSTGRES_USER=labelsure \
  -e POSTGRES_PASSWORD=labelsure \
  -p 5432:5432 postgres:16-alpine
```

Or start your local PostgreSQL and create the database:
```sql
CREATE DATABASE labelsure;
CREATE USER labelsure WITH PASSWORD 'labelsure';
GRANT ALL PRIVILEGES ON DATABASE labelsure TO labelsure;
```

### 5. Run the backend

```bash
# From project root:
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at:
- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Tables are created automatically on first startup.

---

## Setup — Flutter Mobile App

### Prerequisites

- Flutter SDK 3.22+ → https://docs.flutter.dev/get-started/install
- Android Studio (Hedgehog / 2023.x or newer) with:
  - Flutter & Dart plugins installed
  - Android SDK installed (API 34 recommended)
  - At least one AVD (Android Virtual Device) created, or a physical device with USB debugging enabled

---

### Running on Android Studio

#### 1. Open the project

Open **`frontend/`** as the project root in Android Studio — **not** the repository root.

```
File → Open → .../LabelSure/frontend/
```

Android Studio will detect the Flutter project and prompt you to install the Flutter SDK path.

#### 2. Get Flutter dependencies

In the terminal inside Android Studio (or any shell from `frontend/`):

```bash
flutter pub get
```

#### 3. Start the backend (required before running the app)

From the **repo root** in a separate terminal:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

> **`--host 0.0.0.0` is required** — without it, the backend only binds to `127.0.0.1` and the
> Android emulator/device cannot reach it.

#### 4. Configure the backend URL

The app reads the backend URL from a single config constant in
`lib/config/app_config.dart` via `--dart-define`.

**Default (Android Emulator) — no flag needed:**

The default is `http://10.0.2.2:8000` which routes through the Android emulator's
special host gateway back to your development machine's `localhost:8000`.

```bash
# Just run — default works for the emulator:
flutter run
```

**Physical Android Device on the same LAN:**

1. Find your development machine's local IP address:
   - Windows: `ipconfig` → look for "IPv4 Address" (e.g. `192.168.1.42`)
   - macOS/Linux: `ifconfig` → look for `inet` on your Wi-Fi adapter

2. Run with the `--dart-define` flag:

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.42:8000
```

**In Android Studio run configuration:**

```
Run → Edit Configurations → Additional run args:
  --dart-define=API_BASE_URL=http://192.168.1.42:8000
```

**Deployed backend:**

```bash
flutter run --dart-define=API_BASE_URL=https://api.labelsure.example.com
```

#### 5. Run the app

In Android Studio:
- Select your emulator or connected device from the device dropdown
- Click **▶ Run** (or press Shift+F10)

Or from the terminal:

```bash
# List available devices
flutter devices

# Run on a specific device
flutter run -d <device-id>

# Run on emulator with verbose logging
flutter run -d emulator-5554 --verbose
```

#### 6. Build a debug APK

```bash
flutter build apk --debug
# APK at: build/app/outputs/flutter-apk/app-debug.apk

# Install directly on connected device:
flutter install
```

---

### Emulator Camera Note

Android emulators typically do not have a working physical camera. The Scan screen
always shows both **Camera** and **Gallery** options with equal prominence. If camera
capture fails (common on emulators), use **"Choose from Gallery"** to pick a test
image — the compliance pipeline runs identically either way.

Sample test images are in `backend/sample_data/` — transfer them to the emulator
via Android Studio's Device Explorer or:

```bash
adb push backend/sample_data/compliant_label.png /sdcard/Pictures/
```

---

### Network / Cleartext HTTP

The backend runs plain HTTP during development. Android 9+ blocks cleartext traffic
by default. This is handled in two places:

1. `android/app/src/main/res/xml/network_security_config.xml` — allowlist for
   `10.0.2.2` (emulator), `10.0.3.2` (Genymotion), `localhost`, and `.local` mDNS.
2. `android/app/src/main/AndroidManifest.xml` — `android:usesCleartextTraffic="true"`
   as a belt-and-suspenders fallback.

> ⚠️ **Both are marked DEV ONLY.** Remove them and switch to HTTPS before any
> production/Play Store deployment.

---

### App Screens

| Screen | Description |
|--------|-------------|
| **Login** | Sign in / Register with role selection |
| **Scan** | Camera capture or gallery pick → one-tap compliance scan |
| **Scan Result** | COMPLIANT/NON-COMPLIANT badge + full rule checklist + extracted fields |
| **Scan History** | Paginated list (officers see all; consumers see own) |
| **Scan Detail** | Full detail view fetched from API |
| **Profile** | User info and logout |

---

## Setup — Officer Web Dashboard

### Prerequisites

- Node.js 18+

### 1. Install dependencies

```bash
cd web_dashboard
npm install
```

### 2. Run dev server

```bash
npm run dev
```

Dashboard available at: **http://localhost:5174**

> The dev server proxies `/api` → `http://localhost:8000`. The dashboard requires an Officer or Admin role account to log in.

---

## Running with Docker

The easiest way to start PostgreSQL + FastAPI together:

```bash
# From project root:
docker-compose up -d

# View logs:
docker-compose logs -f backend
```

This starts:
- `labelsure_db` on port 5432
- `labelsure_backend` on port 8000

---

## Running Tests

```bash
cd backend
# Activate virtual environment first
pip install pytest pytest-asyncio

python -m pytest tests/ -v
```

Expected output:
```
tests/test_rules_engine.py::TestRule61A::test_pass_with_name_and_address PASSED
tests/test_rules_engine.py::TestRule61A::test_fail_missing_name PASSED
...
tests/test_rules_engine.py::TestEngine::test_fully_compliant_label PASSED
tests/test_field_extractor.py::TestExtractMRP::test_rupee_symbol PASSED
...
40+ passed
```

---

## Sample Label Images

Generate synthetic test labels:

```bash
cd backend
python -m sample_data.generate_labels
```

Generates in `backend/sample_data/`:

| File | Description | Expected Verdict |
|------|-------------|-----------------|
| `compliant_label.png` | All fields present, adequate font | COMPLIANT |
| `noncompliant_mrp.png` | MRP field missing | NON_COMPLIANT (RULE_6_1_D) |
| `noncompliant_date.png` | Manufacture date missing | NON_COMPLIANT (RULE_6_1_E) |
| `noncompliant_addr.png` | Address missing | NON_COMPLIANT (RULE_6_1_A) |
| `blurry_label.png` | Gaussian blur applied | NEEDS_REVIEW |

---

## Rules Encoded

All rules implement **India Legal Metrology (Packaged Commodities) Rules, 2011** (GSR 977(E) dated 24 December 2011).

### Rule 6(1)(a) — `RULE_6_1_A`
**Manufacturer/Packer/Importer Name & Address**
Every package shall bear the name and registered address of the manufacturer, packer, or importer.

### Rule 6(1) — `RULE_6_1_B`
**Generic/Common Name**
The generic or common name of the commodity must be declared on every package.

### Rule 6(1) — `RULE_6_1_C`
**Net Quantity**
The net quantity in standard units of weight (g/kg), volume (ml/L), or number (pcs) must be declared.

### Rule 6(1) — `RULE_6_1_D`
**MRP Inclusive of All Taxes**
The Maximum Retail Price (MRP) inclusive of all taxes must be displayed, prefixed with "MRP".

### Rule 6(1) — `RULE_6_1_E`
**Month & Year of Manufacture**
The month and year of manufacture, packing, or import must be stated.

### Rule 7 / 7(3) — `RULE_7_FONT_HEIGHT`
**Minimum Letter/Numeral Height**

Full lookup table per Rule 7(1) PCR 2011:

| Net Quantity | Printed | Embossed/Moulded/Blown |
|---|---|---|
| ≤ 50 g/ml | **1 mm** | — |
| ≤ 200 g/ml | **2 mm** | **1 mm** |
| ≤ 1 kg/L | **4 mm** | **2 mm** |
| ≤ 10 kg/L | — | **4 mm** |
| > 1 kg/L or > 10 kg/L | **6 mm** | **6 mm** |

### Rule 18(2) — `RULE_18_2`
**Sale Price Must Not Exceed MRP**
No person shall sell any pre-packaged commodity at a price exceeding the declared MRP. Violation is a cognizable offence under Legal Metrology Act 2009, section 36.

---

## API Reference

### Authentication

```
POST /auth/register     Create user account
POST /auth/login        Get JWT token
GET  /auth/me           Get current user profile
```

### Scans

```
POST /scans/upload      Upload label image (multipart/form-data)
                        Form fields:
                          file            (required) JPEG/PNG/WEBP
                          sale_price      (optional) float — enables Rule 18(2)
                          font_type       (optional) "printed" | "embossed"
                          reference_width_mm (optional) — for font height calibration
                          reference_width_px (optional)

GET  /scans             List scans (officer: all; consumer: own)
                        Query: verdict, page, page_size

GET  /scans/{id}        Full scan detail (fields + rule results)
```

### Reports (Officer only)

```
GET  /reports/export    Export CSV or JSON
                        Query: verdict, date_from, date_to, fmt (csv|json)
```

---

## Known Limitations (v1)

1. **Exemptions not implemented:** Small packages below the net quantity threshold (e.g. < 10g/ml for single-serving) and institutional buyer exemptions are **out of scope for v1**.

2. **Font height requires calibration:** Rule 7 font-height measurement is only possible when:
   - The image has valid EXIF DPI data, or
   - A reference object of known physical dimensions is photographed alongside the label, or
   - The package's physical dimensions are entered manually.
   Without calibration, Rule 7 returns an INFO result (not a FAIL).

3. **Curved packaging:** OpenCV geometry measurements may be inaccurate on highly curved surfaces (e.g. cylindrical cans). Results on curved labels should be manually verified.

4. **Indic OCR accuracy:** PaddleOCR supports Hindi, Tamil, Telugu, Kannada, and Malayalam. Bengali, Gujarati, Punjabi, and Odia use English fallback in v1 due to limited model availability. OCR accuracy on handwritten or stylized scripts is lower.

5. **Field extraction heuristics:** The regex-based field extractor works well on standard label formats. Labels with non-standard layouts (e.g. MRP in unusual positions, split across lines) may extract fields incorrectly, triggering NEEDS_REVIEW.

6. **No Expiry Date check:** Expiry/Best Before date checking is not implemented in v1 (not a Rule 6(1) mandatory requirement under PCR 2011 for all commodities).

7. **No country-of-origin check:** This field is not currently extracted or validated.

---

## Project Structure

```
LabelSure/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Settings from .env
│   ├── database.py           # Async SQLAlchemy engine
│   ├── models.py             # ORM: User, Scan, ExtractedField, RuleViolation, AuditLog
│   ├── schemas.py            # Pydantic API schemas
│   ├── auth.py               # JWT auth + RBAC
│   ├── routers/
│   │   ├── auth.py           # POST /auth/login, /register, GET /auth/me
│   │   ├── scans.py          # POST /scans/upload, GET /scans, /scans/{id}
│   │   └── reports.py        # GET /reports/export
│   ├── processing/
│   │   ├── ocr_engine.py     # PaddleOCR + Tesseract fallback
│   │   ├── cv_geometry.py    # OpenCV font-height measurement
│   │   ├── nlp_lang.py       # Language detection (Unicode + langdetect)
│   │   └── field_extractor.py # Regex field extraction from OCR text
│   ├── rules/                # ← Standalone versioned rules engine
│   │   ├── __init__.py
│   │   ├── engine.py         # Main orchestrator
│   │   ├── models.py         # LabelData, RuleResult, Verdict dataclasses
│   │   ├── thresholds.py     # All numeric constants (edit here to update rules)
│   │   ├── rule_6_1.py       # Rule 6(1)(a-e) mandatory field checks
│   │   ├── rule_7.py         # Rule 7 font-height checks
│   │   ├── rule_18_2.py      # Rule 18(2) sale price vs MRP
│   │   └── VERSION           # Rule version string
│   ├── tests/
│   │   ├── test_rules_engine.py   # 40+ unit tests
│   │   └── test_field_extractor.py
│   ├── sample_data/
│   │   └── generate_labels.py    # Synthetic test label generator
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                 # Flutter mobile app (Android + iOS)
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── main.dart         # App entry, GoRouter, theme
│   │   ├── config/
│   │   │   └── app_config.dart   # ← Single source of truth for backend URL
│   │   ├── models/           # scan.dart, user.dart
│   │   ├── services/         # api_service.dart, auth_service.dart
│   │   ├── utils/            # permission_helper.dart
│   │   ├── widgets/          # compliance_badge, rule_checklist, scan_card
│   │   └── screens/          # login, scan, scan_result, scan_history, scan_detail
│   └── android/
│       ├── build.gradle      # root Gradle file
│       ├── settings.gradle
│       ├── gradle.properties
│       └── app/
│           ├── build.gradle  # app-level: minSdk 21, targetSdk 34
│           └── src/main/
│               ├── AndroidManifest.xml      # permissions + cleartext flag
│               ├── kotlin/.../MainActivity.kt
│               └── res/
│                   ├── values/styles.xml
│                   └── xml/network_security_config.xml  # ← DEV cleartext allowlist
│
├── web_dashboard/            # Officer-facing React/Vite web app
│   ├── src/
│   │   ├── App.jsx           # Auth gate + sidebar layout
│   │   ├── index.css         # Full design system
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx # Scan table + filters + export
│   │   │   └── ScanDetail.jsx
│   │   └── services/api.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml        # PostgreSQL + FastAPI
├── .env.example
└── README.md
```

---

## Contributing

1. Fork the repo and create a feature branch.
2. To add or modify a rule, edit `backend/rules/thresholds.py` (for thresholds) or add a new `rule_XX.py` module and register it in `engine.py`.
3. Update the version in `backend/rules/VERSION`.
4. Add corresponding tests in `backend/tests/test_rules_engine.py`.
5. Run `pytest tests/ -v` before opening a PR.
>>>>>>> 267fda3 (feat: initial LabelSure implementation - FastAPI backend + Flutter app + React dashboard)
