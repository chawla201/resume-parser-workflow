# Resume AI Workflow — CLAUDE.md

This file instructs Claude Code on how to build the resume parsing and database ingestion workflow.

> **Constraint:** This workflow must use only open source AI models. No paid proprietary APIs (e.g. Anthropic, OpenAI, Google Gemini) are permitted. All inference runs locally via **Ollama**.

---

## Project overview

Build a CLI workflow that:
1. Accepts a resume file (PDF, DOCX, or TXT) as input
2. Extracts raw text from the document
3. Sends the text to a locally-hosted open source LLM via Ollama and receives a structured JSON object
4. Validates and normalises the JSON against a fixed schema
5. Saves the JSON to an output file
6. Appends the candidate data into two SQL tables: `candidates` and `resumes`

---

## Repository structure

```
resume-workflow/
├── CLAUDE.md
├── README.md
├── pyproject.toml           # or requirements.txt
├── .env.example
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── parser.py            # Document → raw text
│   ├── extractor.py         # Claude API call → JSON
│   ├── validator.py         # JSON schema validation
│   ├── db.py                # SQL insert logic
│   └── models.py            # Pydantic models / schema
├── output/                  # Generated JSON files land here
├── sql/
│   └── schema.sql           # CREATE TABLE statements
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
| LLM runtime | [Ollama](https://ollama.com) (local inference server) |
| LLM model | `mistral` or `llama3` (open source, runs on CPU or GPU) |
| LLM client | `ollama` Python SDK (`pip install ollama`) |
| Document parsing | `pdfplumber` (PDF), `python-docx` (DOCX) |
| JSON validation | `pydantic` v2 |
| Database ORM | `sqlalchemy` 2.x with `psycopg2` (Postgres) or `sqlite3` (local dev) |
| CLI | `typer` |
| Env vars | `python-dotenv` |
| Testing | `pytest` |

---

## Environment variables

Create a `.env` file (copy from `.env.example`):

```
# Ollama server (default when running locally)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral

DATABASE_URL=postgresql://user:password@localhost:5432/resumedb
# For local dev: DATABASE_URL=sqlite:///./dev.db
OUTPUT_DIR=./output
```

No API keys are required. Ollama runs entirely on your machine. Never commit `.env` to version control.

---

## Step 1 — Document parser (`src/parser.py`)

Implement `extract_text(file_path: str) -> str`.

- If the extension is `.pdf`: use `pdfplumber` to read all pages and join their text.
- If the extension is `.docx`: use `python-docx` to iterate paragraphs.
- If the extension is `.txt`: read with `open()` using UTF-8 encoding.
- Raise `ValueError` for unsupported formats.
- Strip excessive whitespace before returning.

---

## Step 2 — LLM extractor (`src/extractor.py`)

Implement `extract_candidate(raw_text: str) -> dict`.

Use the `ollama` Python SDK to call the locally-hosted model configured in `OLLAMA_MODEL` (default: `mistral`). Do **not** use any paid API — all inference must run through Ollama.

### Recommended models (pull before first run)

```bash
ollama pull mistral        # fast, strong at structured output
ollama pull llama3         # alternative if mistral unavailable
```

### System prompt

```
You are a resume parser. Extract structured information from the resume text provided.
Return ONLY a valid JSON object — no markdown fences, no explanation, no preamble.
Follow the schema exactly. If a field is not present in the resume, use null.
```

### User prompt template

```
Extract all candidate information from this resume and return a JSON object with this exact schema:

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
  "education": [
    {
      "institution": "string",
      "degree": "string or null",
      "field_of_study": "string or null",
      "start_year": "int or null",
      "end_year": "int or null"
    }
  ],
  "experience": [
    {
      "company": "string",
      "title": "string",
      "location": "string or null",
      "start_date": "YYYY-MM or null",
      "end_date": "YYYY-MM or null",
      "is_current": "bool",
      "description": "string or null"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuer": "string or null",
      "year": "int or null"
    }
  ]
}

Resume:
{raw_text}
```

### API call

```python
import ollama, json, os

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

def extract_candidate(raw_text: str) -> dict:
    user_prompt = USER_PROMPT_TEMPLATE.format(raw_text=raw_text)

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        format="json",   # Ollama structured output mode — forces valid JSON
    )

    raw = response["message"]["content"]
    return json.loads(raw)
```

The `format="json"` parameter instructs Ollama to constrain the model's output to valid JSON, reducing parse failures. Handle `json.JSONDecodeError` anyway — if parsing fails, log the raw response and raise a descriptive error.

---

## Step 3 — JSON validator (`src/validator.py`)

Define a `CandidateSchema` Pydantic model that mirrors the JSON schema above exactly.

Implement `validate(data: dict) -> CandidateSchema`:
- Parse the dict through the Pydantic model.
- Normalise email to lowercase.
- Normalise phone: strip non-numeric characters except `+` and spaces.
- Return the validated model instance.

---

## Step 4 — Persist JSON to disk

In `main.py`, after validation:
- Generate a filename: `candidate_{uuid4_short}.json`
- Write the validated model to `OUTPUT_DIR/candidate_{id}.json` using `model.model_dump_json(indent=2)`.
- Log the output path.

---

## Step 5 — Database schema (`sql/schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS candidates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name     TEXT NOT NULL,
    email         TEXT,
    phone         TEXT,
    location      TEXT,
    linkedin_url  TEXT,
    github_url    TEXT,
    summary       TEXT,
    skills        TEXT[],          -- array of strings
    languages     TEXT[],
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resumes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    raw_text        TEXT,
    source_filename TEXT,
    json_path       TEXT,
    education       JSONB,
    experience      JSONB,
    certifications  JSONB,
    parsed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_candidate_id ON resumes(candidate_id);
```

For SQLite dev mode: use `TEXT` instead of `UUID`, `TEXT` instead of `TEXT[]`, and `TEXT` instead of `JSONB`. Detect from `DATABASE_URL` prefix.

---

## Step 6 — Database writer (`src/db.py`)

Implement `insert_candidate(candidate: CandidateSchema, source_filename: str, json_path: str, raw_text: str) -> str`.

- Open a SQLAlchemy session.
- Insert a row into `candidates`, capture the returned `id`.
- Insert a row into `resumes` with `candidate_id` as the foreign key.
- Commit the transaction.
- Return the `candidate_id` as a string.
- Wrap in try/except and rollback on failure.

---

## CLI entry point (`src/main.py`)

```
python -m src.main process --file path/to/resume.pdf
```

Full flow:
1. `extract_text(file)` → raw text
2. `extract_candidate(raw_text)` → dict
3. `validate(dict)` → CandidateSchema
4. Save JSON to disk
5. `insert_candidate(...)` → candidate_id
6. Print success summary

Options:
- `--file` (required): path to resume file
- `--dry-run`: run steps 1–4, skip DB insert
- `--output-dir`: override OUTPUT_DIR env var

---

## Error handling

| Error | Behaviour |
|---|---|
| Unsupported file format | `ValueError`, exit code 1 |
| Ollama not running | Clear error: "Ollama server not reachable at {OLLAMA_BASE_URL}. Run `ollama serve`." |
| Ollama model not pulled | Clear error: "Model '{OLLAMA_MODEL}' not found. Run `ollama pull {OLLAMA_MODEL}`." |
| JSON parse failure | Log raw LLM response, raise |
| Pydantic validation failure | Log field errors, raise |
| DB connection failure | Log, raise — do not silently swallow |

---

## Testing

Write pytest tests for each module. Use fixtures and mock the Ollama client in `test_extractor.py` — do not make real LLM calls in tests.

Provide a sample resume text fixture in `tests/fixtures/sample_resume.txt`.

Run tests:
```
pytest tests/ -v
```

---

## Running the workflow

```bash
# 1. Install Ollama (macOS / Linux)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull the model (one-time download)
ollama pull mistral

# 3. Start the Ollama server (runs on http://localhost:11434)
ollama serve

# 4. Install Python dependencies
pip install -e ".[dev]"

# 5. Set up environment
cp .env.example .env
# Edit .env with your DB URL — no API key needed

# 6. Run schema migration
psql $DATABASE_URL -f sql/schema.sql

# 7. Process a resume
python -m src.main process --file ./sample_resume.pdf

# 8. Dry run (no DB write)
python -m src.main process --file ./sample_resume.pdf --dry-run
```

---

## Notes for Claude Code

- **Never use paid AI APIs** (Anthropic, OpenAI, Google Gemini, Cohere, etc.). All inference must go through Ollama.
- The default model is `mistral`. Read `OLLAMA_MODEL` from the environment — never hardcode a model name.
- Use `format="json"` in the `ollama.chat()` call to enable structured output mode.
- Do not hardcode any credentials — only read from environment variables.
- The `output/` directory must be created automatically if it does not exist.
- All DB operations must be transactional — never partial inserts.
- Keep `parser.py`, `extractor.py`, `validator.py`, and `db.py` as independent, testable modules.
- Follow PEP 8; use type hints on all function signatures.

### Code quality standard — OpenAI Codex review

All code generated by Claude Code will be reviewed and scrutinized by **OpenAI Codex**. Write every file as if it is going directly into a production codebase. Specifically:

- **No placeholder logic.** Every function must be fully implemented. No `pass`, `# TODO`, `raise NotImplementedError`, or stub bodies.
- **Type hints everywhere.** All function signatures, return types, and class attributes must be fully annotated. Use `from __future__ import annotations` at the top of each file.
- **Docstrings on every public symbol.** Each module, class, and public function must have a Google-style docstring describing purpose, args, and return value.
- **No bare `except`.** Always catch specific exception types. Log the exception with `logging.exception()` before re-raising or handling.
- **Constants at module level.** No magic strings or numbers inline. Define all literals (model names, table names, field lengths, retry counts) as named constants at the top of the file.
- **Immutable defaults.** Never use mutable default arguments (e.g. `def f(x=[]):`). Use `None` and assign inside the function body.
- **Logging, not print.** Use the standard `logging` module throughout. Never use `print()` for operational output. Configure a logger per module: `logger = logging.getLogger(__name__)`.
- **Single responsibility.** Each function must do exactly one thing. If a function exceeds ~30 lines, refactor it.
- **Transactional safety.** All database writes must use context managers (`with session.begin():`) so rollback is automatic on any exception.
- **No hardcoded paths.** All file paths must be constructed using `pathlib.Path`, never string concatenation.
- **Graceful shutdown.** The CLI must handle `KeyboardInterrupt` cleanly and exit with a non-zero code without printing a traceback.
