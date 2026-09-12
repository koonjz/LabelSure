# LabelSure

**AI-powered compliance scanner for India's Legal Metrology (Packaged Commodities) Rules, 2011**

LabelSure helps Legal Metrology enforcement officers, manufacturers, and e-commerce sellers instantly verify whether a packaged-product label complies with the PCR 2011 Rules — using on-device ML Kit OCR, server-side computer vision/OCR fallback, and a standalone deterministic rules engine.

---

## Table of Contents

1. [Architecture & Scan Flow](#architecture--scan-flow)
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
12. [Contributing](#contributing)

---

## Architecture & Scan Flow

LabelSure supports a **dual-path architecture** designed for both ultra-fast mobile execution and high-accuracy desktop/server analysis:

```
Flutter Mobile App (Android/iOS)               React Officer Web Dashboard
   │                                                    │
   ├───────────────────────────────┐                    │
   │ [Fast Path: On-Device OCR]    │ [Fallback Path]    │ [Full Image Upload]
   │ (Google ML Kit Latin/Indic)   │ (Compressed Image) │
   │                               │                    │
   ▼                               ▼                    ▼
POST /scans/analyze-text         POST /scans/upload  (multipart/form-data)
(Sends ~1KB text payload)        (Sends image file)
   │                               │
   │                     ┌─────────┴─────────┐
   │                     │  FastAPI Backend  │
   │                     │  (Python 3.11)    │
   │                     └─────────┬─────────┘
   │                               │
   │                    ┌──────────┴──────────┐
   │                    │ Server OCR Engine   │
   │                    │ (PaddleOCR / Tesseract)
   │                    └──────────┬──────────┘
   │                               │
   └───────────────┬───────────────┘
                   │
          ┌────────▼────────┐
          │ Field Extractor │ (Regex & NLP parsing)
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │  Rules Engine   │ (Standalone Legal Metrology PCR 2011)
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │   PostgreSQL    │ (Scans, Violations, Fields, Audit Logs)
          └─────────────────┘
```

---

## Setup — Backend

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or use Docker — see below)
- Tesseract OCR (for fallback OCR on server)

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

> **Note:** PaddleOCR models are downloaded automatically on first run. If PaddleOCR is unavailable, Tesseract is used as fallback.

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

---

## Setup — Flutter Mobile App

### Prerequisites

- Flutter SDK 3.22+ → https://docs.flutter.dev/get-started/install
- Android Studio (2023.x or newer) with Android SDK (API 34 recommended)

---

### Running on Android Studio

#### 1. Open the project

Open **`frontend/`** as the project root in Android Studio.

#### 2. Get Flutter dependencies

```bash
cd frontend
flutter pub get
```

#### 3. Start the backend

```bash
# From repo root:
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. Configure the backend URL

The app reads the backend URL via `--dart-define=API_BASE_URL=...`.

- **Android Emulator (default):** `http://10.0.2.2:8000` (works automatically without flags)
- **Physical Device over Wi-Fi:**
  ```bash
  flutter run --dart-define=API_BASE_URL=http://<YOUR_LOCAL_IP>:8000
  ```
- **Deployed Backend (e.g. Render / Cloud):**
  ```bash
  flutter run --dart-define=API_BASE_URL=https://your-backend.onrender.com
  ```

#### 5. On-Device OCR (Google ML Kit)

The Flutter mobile application includes on-device text recognition using Google ML Kit (`google_mlkit_text_recognition`):
- **Zero latency**: OCR runs on-device in ~100-300ms.
- **Low bandwidth**: Only the parsed text (~1KB) is sent to `POST /scans/analyze-text`.
- **Offline/Hybrid resilience**: If on-device recognition produces insufficient text, the app automatically compresses the image and falls back to server-side OCR.

---

### App Screens

| Screen | Description |
|--------|-------------|
| **Login** | Sign in / Register with role selection (Officer / Consumer) |
| **Scan** | On-device ML Kit OCR with camera capture or gallery pick |
| **Scan Result** | Real-time COMPLIANT/NON-COMPLIANT verdict, detailed rule breakdown, and extracted attributes |
| **Scan History** | Paginated scan history with filtering (Officers see all; Consumers see own) |
| **Scan Detail** | Detailed view of any historical scan |
| **Profile** | User profile and session management |

---

## Setup — Officer Web Dashboard

### Prerequisites

- Node.js 18+

### 1. Install dependencies & run

```bash
cd web_dashboard
npm install
npm run dev
```

Dashboard available at: **http://localhost:5174**

---

## Running with Docker

```bash
# From project root:
docker-compose up -d

# View logs:
docker-compose logs -f backend
```

---

## Running Tests

```bash
# From project root:
pytest backend/tests/ -v
```

Tests cover 104+ test cases across:
- `test_rules_engine.py` (Rule 6(1)(a-e), Rule 7 font heights, Rule 18(2) MRP vs sale price, multi-rule verdicts)
- `test_field_extractor.py` (MRP regex, Net quantity, Mfg date variations, multi-lingual labels)
- `test_database_config.py` (URL sanitization, async driver normalization)

---

## Sample Label Images

Generate synthetic test labels:

```bash
python -m backend.sample_data.generate_labels
```

Generates in `backend/sample_data/`:
- `compliant_label.png` (Fully compliant label)
- `noncompliant_mrp.png` (Missing MRP)
- `noncompliant_date.png` (Missing manufacturing date)
- `noncompliant_addr.png` (Missing manufacturer address)
- `blurry_label.png` (Low confidence test)

---

## Rules Encoded

All rules implement **India Legal Metrology (Packaged Commodities) Rules, 2011** (GSR 977(E) dated 24 December 2011):

- **Rule 6(1)(a) (`RULE_6_1_A`)**: Manufacturer, packer, or importer name and complete registered address.
- **Rule 6(1)(b) (`RULE_6_1_B`)**: Generic or common name of the packaged commodity.
- **Rule 6(1)(c) (`RULE_6_1_C`)**: Net quantity in standard metric units (g, kg, ml, L, pcs).
- **Rule 6(1)(d) (`RULE_6_1_D`)**: Maximum Retail Price (MRP) inclusive of all taxes.
- **Rule 6(1)(e) (`RULE_6_1_E`)**: Month and year of manufacture, packing, or import.
- **Rule 7 / 7(3) (`RULE_7_FONT_HEIGHT`)**: Minimum numeral and letter font height lookup matrix based on net quantity package weight.
- **Rule 18(2) (`RULE_18_2`)**: Sale price must not exceed declared MRP (cognizable violation under Sec 36, LM Act 2009).

---

## API Reference

### Authentication

```http
POST /auth/register     Create user account
POST /auth/login        Get JWT access token
GET  /auth/me           Get current user profile
```

### Scans

```http
POST /scans/analyze-text  Fast path: Analyze pre-extracted OCR text from on-device ML Kit
                          Body: { "ocr_text": "...", "lang_code": "en", "sale_price": 50.0 }

POST /scans/upload        Upload label image (multipart/form-data)
                          Form: file, sale_price, font_type, reference_width_mm

GET  /scans               List scans (officer: all; consumer: own)
GET  /scans/{id}          Full scan detail (extracted fields + rule violations)
```

### Reports (Officer only)

```http
GET  /reports/export      Export CSV or JSON
```

---

## Known Limitations (v1)

1. **Small package exemptions**: Exemptions below threshold (< 10g/ml) are reserved for future versions.
2. **Font height calibration**: Physical height measurement requires DPI data or known reference width.
3. **Curved surfaces**: Highly curved cylindrical packaging may need flat re-capturing.
4. **Non-standard label layouts**: Complex, scattered, or decorative fonts may prompt manual review.

---

## Project Structure

```
LabelSure/
├── backend/
│   ├── main.py               # FastAPI app entry point & middleware
│   ├── config.py             # Settings & environment configuration
│   ├── database.py           # Async SQLAlchemy engine & session maker
│   ├── models.py             # ORM: User, Scan, ExtractedField, RuleViolation, AuditLog
│   ├── schemas.py            # Pydantic schemas (incl. TextScanRequest)
│   ├── auth.py               # JWT auth & role-based access control (RBAC)
│   ├── routers/
│   │   ├── auth.py           # /auth endpoints
│   │   ├── scans.py          # /scans/upload, /scans/analyze-text, /scans list/detail
│   │   └── reports.py        # /reports/export
│   ├── processing/
│   │   ├── ocr_engine.py     # Server-side PaddleOCR + Tesseract fallback
│   │   ├── cv_geometry.py    # OpenCV font-height measurement
│   │   ├── nlp_lang.py       # Language detection (Unicode + langdetect)
│   │   └── field_extractor.py # Regex field extraction from OCR text
│   ├── rules/                # Standalone deterministic rules engine
│   │   ├── engine.py         # Main orchestrator
│   │   ├── models.py         # LabelData, RuleResult, Verdict dataclasses
│   │   ├── thresholds.py     # Numeric thresholds & lookups
│   │   ├── rule_6_1.py       # Rule 6(1)(a-e) checks
│   │   ├── rule_7.py         # Rule 7 font height checks
│   │   ├── rule_18_2.py      # Rule 18(2) sale price vs MRP check
│   │   └── VERSION           # Rule version tag
│   └── tests/
│       ├── test_rules_engine.py
│       ├── test_field_extractor.py
│       └── test_database_config.py
│
├── frontend/                 # Flutter mobile app (Android & iOS)
│   ├── pubspec.yaml
│   └── lib/
│       ├── main.dart         # Entry point & theme setup
│       ├── config/           # App routes & API config
│       ├── models/           # Scan and User data models
│       ├── services/         # on-device ocr_service.dart, api_service.dart, auth_service.dart
│       ├── widgets/          # compliance_badge, rule_checklist, scan_card
│       └── screens/          # login, scan, scan_result, scan_history, scan_detail
│
├── web_dashboard/            # Officer React/Vite dashboard
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/            # Login, Dashboard, ScanDetail
│   │   └── services/api.js
│   └── package.json
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Contributing

1. Fork the repo and create a feature branch (`git checkout -b feature/new-feature`).
2. To add or update a rule, modify `backend/rules/thresholds.py` or create a new `rule_XX.py` module and register it in `engine.py`.
3. Add or update tests in `backend/tests/`.
4. Run `pytest backend/tests/ -v` and `flutter analyze` before opening a pull request.
