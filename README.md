**Digital Forensics File Analysis System**

ForenScan is a self-hosted web application for forensic-grade file analysis. It detects file types via magic-number matching, computes cryptographic hashes, visualises raw hex data, flags anomalies, and now includes an AI assistant (powered by Groq / LLaMA 3.3) that explains findings in plain English and answers analyst questions via a built-in chatbot.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [AI Features Setup](#ai-features-setup)
- [Analysis Pipeline](#analysis-pipeline)
- [Signature Database](#signature-database)
- [Export & Chain of Custody](#export--chain-of-custody)
- [Security Notes](#security-notes)
- [Project Structure](#project-structure)
- [Glossary](#glossary)

---

## Features

| Feature | Details |
|---|---|
| **Magic Number Detection** | Longest-match algorithm against 185+ signatures across 19 categories |
| **Cryptographic Hashing** | Streaming MD5 + SHA-256 in 64 KB chunks — memory-safe for large files |
| **Hex Visualisation** | xxd-compatible address / hex / ASCII display of first 64 bytes |
| **Anomaly Detection** | Extension mismatch, executable-in-document, high entropy, YARA-lite string patterns |
| **Footer Validation** | Verifies file tail bytes against known format footers (JPEG, ZIP, PDF, GIF, etc.) |
| **Entropy Analysis** | Shannon entropy per file — values above 7.2 bits/byte flagged as possibly encrypted or packed |
| **Directory Scan** | Recursive scan up to 500 files with symlink skipping and size caps |
| **Scan History** | Full session history with per-session risk summary |
| **Signature Management** | Add, edit, delete custom signatures via the web UI with full validation |
| **Export** | JSON (chain-of-custody envelope) and CSV (Autopsy/FTK compatible) |
| **AI Explanation** | One-click plain-English breakdown of any scan via Groq LLaMA 3.3 |
| **AI Chatbot** | Context-aware forensic assistant — ask questions about any scan result |

---
<img width="2752" height="1492" alt="forenscan_ai png" src="https://github.com/user-attachments/assets/b58aab54-9746-4628-82dd-e46327d20e4c" /># ForenScan
---

## Architecture

```
forenscan/
├── app.py                  # Flask application, all routes
├── analyzer.py             # Core analysis engine
├── ai_utils.py             # Groq AI explanation + chatbot
├── config.py               # Paths, limits, constants
├── forensic_signatures.db  # SQLite — signatures + scan results
│
├── utils/
│   ├── hash_utils.py       # Streaming MD5 + SHA-256
│   ├── hex_utils.py        # xxd-style hex formatter
│   └── export_utils.py     # JSON + CSV serialisation
│
├── templates/
│   ├── base.html
│   ├── index.html          # Dashboard + upload forms
│   ├── results.html        # Scan results + AI panel + chatbot
│   ├── history.html        # Scan session history
│   ├── signatures.html     # Signature database browser
│   └── add_signature.html  # Add / edit signature form
│
└── static/
    ├── css/theme.css       # Full design system (dark terminal theme)
    └── js/app.js           # Drag-drop, spinners, hash copy, collapse
```

**Data flow for a single file scan:**

```
Upload → Extension check → Save with UUID prefix
       → Magic number match (SQLite signatures)
       → Footer validation
       → MD5 + SHA-256 (streaming)
       → Hex preview (first 64 bytes)
       → Entropy calculation (first 64 KB)
       → YARA-lite string scan
       → Anomaly scoring
       → Persist to scan_results table
       → Redirect to results page
```

---

## Requirements

- Python 3.11+
- pip packages listed below
- A free [Groq API key](https://console.groq.com) for AI features (optional — app works fully without it)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/forenscan.git
cd forenscan
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install flask flask-limiter werkzeug groq
```

Full requirements for a pinned install:

```
flask>=3.0
flask-limiter>=3.5
werkzeug>=3.0
groq>=0.9
```

### 4. Create required directories

```bash
mkdir -p uploads reports evidence
```

---

## Configuration

All configuration lives in `config.py`:

```python
DB_PATH          = "forensic_signatures.db"   # SQLite database path
UPLOAD_DIR       = "uploads"                  # Temp storage for uploaded files
REPORTS_DIR      = "reports"                  # Export output directory

MAX_UPLOAD_SIZE  = 50 * 1024 * 1024           # 50 MB upload cap
MAX_FILE_SIZE_SCAN = 500 * 1024 * 1024        # 500 MB — skip larger files in dir scan
MAX_DIR_FILES    = 500                        # Max files per directory scan

ALLOWED_SCAN_ROOTS = [                        # Whitelist for directory scan paths
    "evidence",
    "/tmp/forensic_evidence",
]

BLOCKED_UPLOAD_EXTENSIONS = {                 # Extensions rejected on upload
    '.php', '.py', '.rb', '.sh', '.exe', ...
}
```

**To add an allowed scan directory**, append its absolute path to `ALLOWED_SCAN_ROOTS`. Directory scans outside this whitelist are blocked.

---

## Running the App

### Development

```bash
export FORENSCAN_SECRET_KEY="change-me-to-a-long-random-string"
export GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxx"   # optional — for AI features
python app.py
```

App starts at **http://localhost:5050**

### Production (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5050 app:app
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `FORENSCAN_SECRET_KEY` | Recommended | Flask session secret. If unset, an ephemeral key is generated (sessions reset on restart). |
| `GROQ_API_KEY` | Optional | Enables AI explanation and chatbot. Get free at [console.groq.com](https://console.groq.com). |

---

## AI Features Setup

ForenScan uses the **Groq free tier** with `llama-3.3-70b-versatile`. No credit card is required.

### Steps

1. Sign up at [console.groq.com](https://console.groq.com)
2. Go to **API Keys → Create API Key**
3. Set the key in your environment:

```bash
export GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxx"
```

4. Install the Groq library:

```bash
pip install groq
```

### What the AI does

**Explain with AI** (button on every results page)
- Sends the scan metadata (no raw file bytes) to the LLM
- Returns a structured breakdown: overview, risk verdict, per-file explanation with key indicators, and recommended next steps
- Loaded lazily — only called when you click the button

**ForenScan AI Chatbot** (floating widget, bottom-right of results page)
- Context-aware: the full scan data is injected as system context on every turn
- Ask anything: *"Why is this file flagged HIGH?"*, *"What does entropy of 7.8 mean?"*, *"Should I quarantine this?"*
- Conversation history is maintained client-side for the session (last 10 turns)

### Groq free tier limits

| Limit | Value |
|---|---|
| Requests per day | 14,400 |
| Tokens per minute | 6,000 |
| Tokens per day | 500,000 |

This is sufficient for continuous use in a single-analyst forensic workflow.

---

## Analysis Pipeline

### 1. Magic Number Detection

File signatures are matched against the SQLite `signatures` table using a **longest-match-wins** strategy — the signature with the most matching header bytes wins. For ambiguous magic bytes (e.g. `50 4B 03 04` shared by ZIP, DOCX, XLSX, JAR, APK), the declared file extension is used to disambiguate.

Supported categories: `IMAGE`, `DOCUMENT`, `ARCHIVE`, `EXECUTABLE`, `SCRIPT`, `MEDIA`, `SYSTEM`, `CRYPTO`, `FORENSIC`, `FONT`, `DATABASE`, `CAD`, `GIS`, `GAME`, `CONTAINER`, `MOBILE`, `WEB`, `EMAIL`, `DISK`

### 2. Hash Computation

MD5 and SHA-256 are computed simultaneously in a single streaming pass using 64 KB chunks. This is memory-safe for files up to the 500 MB scan limit and meets NIST forensic standards for hash-based evidence integrity.

### 3. Hex Visualisation

The first 64 bytes are rendered in xxd-compatible format:

```
0x0000  FF D8 FF E0 00 10 4A 46  49 46 00 01 01 00 00 01  ......JFIF......
0x0010  00 01 00 00 FF E1 00 16  45 78 69 66 00 00 49 49  ........Exif..II
```

Click any hash value in the results to copy it to your clipboard.

### 4. Anomaly Detection

Four anomaly checks run on every file:

| Check | Trigger | Risk Escalation |
|---|---|---|
| **Extension mismatch** | Detected type category doesn't match declared extension (e.g. EXE disguised as JPG) | CRITICAL |
| **Script in non-script** | Script file with image/archive extension | HIGH |
| **High entropy** | Shannon entropy > 7.2 bits/byte on non-archive files | HIGH |
| **YARA-lite strings** | Suspicious Win32 API strings: `CreateRemoteThread`, `VirtualAlloc`, `WScript.Shell`, `cmd.exe /c` | HIGH |

### 5. Footer Validation

For file types with known footers (JPEG ends `FF D9`, ZIP ends `50 4B 05 06`, etc.), the last N bytes of the file are compared against the expected footer. A `footer_valid = False` combined with an anomaly flag is a strong indicator of file masquerading.

| Value | Meaning |
|---|---|
| `Yes` | File ends with expected footer bytes — structurally intact |
| `No` | Footer bytes don't match — file may be truncated, corrupted, or masquerading |
| `N/A` | This file type has no footer defined in the signature |

---

## Signature Database

The SQLite `signatures` table ships with 185+ entries. You can manage them via the **Signatures** page in the UI.

### Schema

```sql
CREATE TABLE signatures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,           -- e.g. "JPEG Image"
    category    TEXT NOT NULL,           -- e.g. "IMAGE"
    mime_type   TEXT NOT NULL,           -- e.g. "image/jpeg"
    header_hex  TEXT NOT NULL,           -- e.g. "FF D8 FF"
    footer_hex  TEXT,                    -- e.g. "FF D9" (nullable)
    extensions  TEXT NOT NULL,           -- JSON array e.g. '["jpg","jpeg"]'
    risk_level  TEXT NOT NULL            -- CRITICAL | HIGH | MEDIUM | LOW
);
```

### Adding a custom signature

Go to **Signatures → Add Signature** and fill in:
- **Header Hex** — the magic bytes in hex, space-separated (e.g. `89 50 4E 47`)
- **Footer Hex** — optional end-of-file bytes
- **Extensions** — comma-separated, without dots (e.g. `png, apng`)
- **Risk Level** — `CRITICAL` is reserved for `EXECUTABLE` and `SCRIPT` categories

The UI validates your hex in real-time and checks for duplicate signatures before saving.

---

## Export & Chain of Custody

Every scan can be exported from the results page or scan history.

### JSON export

Wraps results in a chain-of-custody envelope:

```json
{
  "forenscan_version": "1.0",
  "export_timestamp": "2025-04-27T10:30:00Z",
  "scan_id": "uuid-v4",
  "chain_of_custody": {
    "analyst": "automated",
    "tool": "ForenScan",
    "hash_algorithm": "MD5+SHA256"
  },
  "results": [ ... ]
}
```

### CSV export

Flat-file export compatible with **Autopsy**, **FTK**, and other forensic platforms. Columns: `scan_id`, `filename`, `filepath`, `detected_type`, `mime_type`, `declared_ext`, `risk_level`, `anomaly_flag`, `anomaly_reason`, `md5_hash`, `sha256_hash`, `file_size`, `scan_timestamp`, `footer_valid`.

---

## Security Notes

- **Path traversal protection** — directory scans are validated against `ALLOWED_SCAN_ROOTS` using `os.path.realpath`. Paths outside the whitelist are rejected.
- **Upload filtering** — server-executable extensions (`.php`, `.py`, `.sh`, `.exe`, etc.) are blocked on upload.
- **Filename sanitisation** — uploaded files are saved as `{uuid}_{secure_filename}`, never using the original filename as a path component.
- **Rate limiting** — scan endpoints are rate-limited (10/min for file scan, 5/min for directory scan, 60/hr for chat).
- **Temporary file cleanup** — uploaded files are automatically deleted 5 minutes after analysis.
- **UUID validation** — all `scan_id` values are validated against a strict UUID v4 regex before use in SQL queries or filenames.
- **AI privacy** — only file metadata (name, type, hashes, flags) is sent to the AI. Raw file bytes never leave the server.

---

## Project Structure

```
forenscan/
├── app.py                   # Flask app + all routes
├── analyzer.py              # ForensicAnalyzer engine
├── ai_utils.py              # Groq AI — explain_scan() + chat()
├── config.py                # Central configuration
├── forensic_signatures.db   # SQLite database (signatures + results)
│
├── utils/
│   ├── hash_utils.py
│   ├── hex_utils.py
│   └── export_utils.py
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── results.html
│   ├── history.html
│   ├── signatures.html
│   └── add_signature.html
│
├── static/
│   ├── css/theme.css
│   └── js/app.js
│
├── uploads/                 # Temp upload storage (auto-cleaned)
├── reports/                 # JSON/CSV export output
└── evidence/                # Default allowed scan root
```

---

## Glossary

**Magic number** — the first few bytes of a file that identify its format, independent of the file extension. E.g. all JPEG files start with `FF D8 FF`.

**Entropy** — a measure of randomness in the file's byte distribution (Shannon entropy, 0–8 bits/byte). Normal files score 4–7. Encrypted or compressed data scores close to 8. A high-entropy non-archive file is suspicious.

**Footer / magic tail** — some formats define both a header and a closing byte sequence. Validating both ends confirms the file is structurally complete.

**YARA-lite** — a simplified string-pattern scan inspired by YARA rules. ForenScan scans for known malicious Win32 API strings without requiring the full YARA engine.

**Chain of custody** — a documented record proving that digital evidence has not been altered. The JSON export includes timestamps, tool version, and hash algorithms used.

**Anomaly flag** — set when any of the four anomaly checks fire. Anomalous files are highlighted in red in the results UI.

**Scan ID** — a UUID v4 generated per scan session, used to group results, link exports, and serve as the URL key for the results page.
