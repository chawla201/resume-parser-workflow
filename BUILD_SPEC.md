# Resume AI Workflow — Build Specification

This file describes the complete architecture and implementation details of the resume parsing and browser UI workflow.

> **Constraint:** All LLM inference must run through **Ollama** (local). No paid proprietary APIs (Anthropic, OpenAI, Google Gemini, Cohere, etc.) are permitted.

---

## Project overview

A browser-based workflow that:
1. Accepts a resume file (PDF, DOCX, or TXT) via a React UI
2. Sends it to a FastAPI backend over REST
3. Extracts raw text from the document
4. Sends the text to a locally-hosted LLM via Ollama and receives a structured JSON object
5. Validates and normalises the JSON against a fixed Pydantic schema
6. Saves the validated JSON to an `output/` file on disk
7. Returns the structured data to the browser — **no database insert** is performed
8. Provides a separate page to browse all previously parsed candidates from the `output/` directory

---

## Repository structure

```
resume-parser-workflow/
├── CLAUDE.md
├── BUILD_SPEC.md
├── README.md
├── package.json             # root: concurrently dev script
├── pyproject.toml
├── .env.example
├── src/
│   ├── __init__.py
│   ├── api.py               # FastAPI application (primary entry point)
│   ├── main.py              # CLI entry point (dry-run only in UI mode)
│   ├── parser.py            # Document → raw text
│   ├── extractor.py         # Ollama call → JSON dict
│   ├── validator.py         # Pydantic validation + normalisation
│   ├── db.py                # SQLAlchemy ORM (used only for CLI path)
│   ├── models.py            # Pydantic models / schema
│   └── logging_config.py   # Structured JSON logging
├── output/                  # Parsed JSON files land here (source of truth for UI)
├── sql/
│   └── schema.sql
├── frontend/
│   ├── index.html
│   ├── package.json         # react, react-dom, react-router-dom; vite
│   ├── vite.config.js       # proxy /api and /health → http://localhost:8000
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   └── client.js    # fetch wrapper; always sends ?dry_run=true
│       ├── pages/
│       │   ├── UploadPage.jsx
│       │   └── CandidatesPage.jsx
│       ├── components/
│       │   ├── NavBar.jsx
│       │   ├── DropZone.jsx
│       │   ├── LoadingSpinner.jsx
│       │   ├── ErrorBanner.jsx
│       │   ├── CandidateDetail.jsx
│       │   ├── CandidateTable.jsx
│       │   ├── JsonView.jsx
│       │   ├── SkillTag.jsx
│       │   ├── EducationCard.jsx
│       │   ├── ExperienceCard.jsx
│       │   ├── CertificationCard.jsx
│       │   ├── CandidateListTable.jsx
│       │   └── Pagination.jsx
│       └── styles/          # plain CSS per component
└── tests/
    ├── test_parser.py
    ├── test_extractor.py
    ├── test_validator.py
    └── test_db.py
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI + Uvicorn |
| LLM runtime | Ollama (local inference server) |
| LLM model | `mistral` or `llama3` (read from `OLLAMA_MODEL` env var) |
| LLM client | `ollama` Python SDK |
| Document parsing | `pdfplumber` (PDF), `python-docx` (DOCX) |
| JSON validation | `pydantic` v2 |
| Database ORM | SQLAlchemy 2.x (used only in CLI path; UI path bypasses DB) |
| CLI | `typer` |
| Env vars | `python-dotenv` |
| Testing | `pytest` |
| Frontend | React 18 + Vite 5 |
| Frontend routing | React Router v6 |
| Dev orchestration | `concurrently` (npm) |

---

## Environment variables

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
DATABASE_URL=sqlite:///./dev.db   # only needed for CLI path
OUTPUT_DIR=./output
```

Copy `.env.example` → `.env`. No API keys required.

---

## Backend — `src/api.py`

### CORS

CORS middleware is added immediately after `app = FastAPI(...)`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{status, ollama, db}` |
| `POST` | `/api/v1/parse` | Upload resume; parse + write JSON; skip DB insert |
| `GET` | `/api/v1/candidates` | List candidates from `output/` JSON files (paginated) |
| `GET` | `/api/v1/candidates/{id}` | Fetch single candidate from `output/{id}.json` |

### `POST /api/v1/parse`

- Always called with `?dry_run=true` from the frontend client.
- Validates file extension, extracts text, calls Ollama, validates with Pydantic.
- Writes output to `OUTPUT_DIR/candidate_{short_uuid}.json`.
- Returns `{candidate_id: null, candidate: {...}, json_path, dry_run: true}`.
- DB insert code is still present for CLI compatibility but is never triggered from the UI.

### `GET /api/v1/candidates`

Reads from the filesystem — **not the database**:

```python
def _sorted_output_files() -> list[Path]:
    files = list(OUTPUT_DIR.glob("*.json"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files
```

- Supports `limit` (1–100, default 20) and `offset` (default 0) query params.
- Returns `{total, limit, offset, items[]}`.
- Each item includes all `CandidateSchema` fields plus:
  - `id`: filename stem (e.g. `candidate_abc12345`)
  - `parsed_at`: file modification time as ISO 8601 string
  - `source_filename`: filename (e.g. `candidate_abc12345.json`)

### `GET /api/v1/candidates/{id}`

- Looks up `OUTPUT_DIR/{id}.json`.
- Returns 404 if the file does not exist.
- Returns the same shape as items in the list endpoint.

### Internal helper — `_read_json_file(path)`

```python
def _read_json_file(path: Path) -> dict | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.timezone.utc)
    data["id"] = path.stem
    data["parsed_at"] = mtime.isoformat()
    data["source_filename"] = path.name
    return data
```

---

## Backend — `src/validator.py`

### List field normalisation

The LLM occasionally returns `null` for array fields (`skills`, `languages`, `education`, `experience`, `certifications`). Pydantic's `default_factory=list` only activates for **absent** keys, not explicit `None`. The `_normalise_fields` function coerces `None` to `[]` for all list fields before Pydantic validation:

```python
LIST_FIELDS = frozenset({"skills", "languages", "education", "experience", "certifications"})

for field in LIST_FIELDS:
    if normalised.get(field) is None:
        normalised[field] = []
```

---

## Backend — `src/parser.py`

`extract_text(file_path: str) -> str`

- `.pdf` → `pdfplumber`, join all pages
- `.docx` → `python-docx`, iterate paragraphs
- `.txt` → `open()` UTF-8
- Raises `ValueError` for unsupported formats
- Strips excessive whitespace before returning

---

## Backend — `src/extractor.py`

`extract_candidate(raw_text: str) -> dict`

Uses `ollama.chat()` with `format="json"` (structured output mode). Model is always read from `OLLAMA_MODEL` env var. Never hardcode a model name.

### System prompt

```
You are a resume parser. Extract structured information from the resume text provided.
Return ONLY a valid JSON object — no markdown fences, no explanation, no preamble.
Follow the schema exactly. If a field is not present in the resume, use null.
```

### JSON schema sent to LLM

```json
{
  "full_name": "string",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "linkedin_url": "string or null",
  "github_url": "string or null",
  "summary": "string or null",
  "skills": ["string"],
  "languages": ["string"],
  "education": [{"institution": "string", "degree": "string or null", "field_of_study": "string or null", "start_year": "int or null", "end_year": "int or null"}],
  "experience": [{"company": "string", "title": "string", "location": "string or null", "start_date": "YYYY-MM or null", "end_date": "YYYY-MM or null", "is_current": "bool", "description": "string or null"}],
  "certifications": [{"name": "string", "issuer": "string or null", "year": "int or null"}]
}
```

---

## Frontend — React + Vite

### Dev setup

Root `package.json` uses `concurrently` to start both servers:

```json
{
  "scripts": {
    "dev": "concurrently \"uvicorn src.api:app --reload --port 8000\" \"cd frontend && npm run dev\""
  },
  "devDependencies": { "concurrently": "^8.2.0" }
}
```

Vite proxy in `frontend/vite.config.js` routes API requests to the backend:

```js
proxy: {
  '/api': { target: 'http://localhost:8000', changeOrigin: true },
  '/health': { target: 'http://localhost:8000', changeOrigin: true }
}
```

### API client — `frontend/src/api/client.js`

- All paths are relative (e.g. `/api/v1/candidates`) — Vite proxy handles routing.
- `parseResume(file, signal)`: always appends `?dry_run=true`; uses `FormData`; does **not** set `Content-Type` manually (browser sets boundary).
- `getCandidates(limit, offset, signal)`: fetches the paginated list.
- `getCandidate(id, signal)`: fetches a single candidate by filename stem.
- Throws `ApiError` (custom class with `status` + `message`) for non-2xx responses.

### Component hierarchy

```
App
├── NavBar ("Upload Resume" | "All Candidates")
├── Route "/"  → UploadPage
│   ├── DropZone (drag-drop or click; validates .pdf/.docx/.txt)
│   ├── LoadingSpinner (shown during Ollama inference, 5–30 s)
│   ├── ErrorBanner (API/network errors)
│   └── CandidateDetail (after successful parse)
│       ├── Tab "Structured" → CandidateTable
│       │   ├── SkillTag[]
│       │   ├── EducationCard[]
│       │   ├── ExperienceCard[]
│       │   └── CertificationCard[]
│       └── Tab "Raw JSON" → JsonView
└── Route "/candidates" → CandidatesPage
    ├── CandidateListTable (Name, Email, Location, Skills, Parsed Date; row click → expand)
    ├── CandidateDetail (inline expand; same shared component)
    └── Pagination (Prev/Next + "Showing X–Y of Z")
```

---

## Data flow (UI path)

```
Browser upload
  → POST /api/v1/parse?dry_run=true
    → extract_text()
    → extract_candidate()  [Ollama]
    → validate()           [Pydantic; None list fields → []]
    → write output/<id>.json
    → return JSON (no DB write)
  ← structured candidate data displayed in browser

Browser navigates to /candidates
  → GET /api/v1/candidates
    → glob output/*.json, sort by mtime desc, paginate
    → return items[]
  ← table of all parsed candidates

Row click
  → GET /api/v1/candidates/<stem>
    → read output/<stem>.json
  ← inline detail panel
```

---

## Error handling

| Error | Behaviour |
|---|---|
| Unsupported file format | `400 Bad Request` |
| Empty extracted text | `400 Bad Request` |
| Ollama not running | `502 Bad Gateway` |
| Pydantic validation failure | `422 Unprocessable Entity` |
| LLM returns `null` for list field | Coerced to `[]` in `_normalise_fields` before validation |
| Candidate file not found | `404 Not Found` |
| Unreadable JSON file in output/ | Skipped silently; logged as warning |

---

## Code quality standards

- `from __future__ import annotations` at the top of every Python file.
- Google-style docstrings on every public module, class, and function.
- `logger = logging.getLogger(__name__)` per module; no `print()` for operational output.
- Specific exception types only — no bare `except`.
- All DB writes use `with session.begin():` for automatic rollback.
- All paths via `pathlib.Path` — no string concatenation.
- Constants at module level — no inline magic strings.
- Functions ≤ ~30 lines; single responsibility.
- `KeyboardInterrupt` caught in CLI; exits non-zero without traceback.
- Mutable default arguments forbidden.

---

## Running the workflow

```bash
# 1. Install Ollama (macOS)
brew install ollama

# 2. Pull the model (one-time download)
ollama pull mistral

# 3. Install Python dependencies
pip install -e ".[dev]"

# 4. Set up environment
cp .env.example .env

# 5. Install Node.js (if not installed)
brew install node

# 6. Install npm dependencies
npm install
cd frontend && npm install && cd ..

# 7. Start backend + frontend together
npm run dev
# Backend:  http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Testing

```bash
pytest tests/ -v
```

- Mock the Ollama client in `test_extractor.py` — no real LLM calls in tests.
- Sample resume fixture: `tests/fixtures/sample_resume.txt`.
