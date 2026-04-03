# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Hard constraint:** All LLM inference must run through **Ollama** (local). Never use paid AI APIs — Anthropic, OpenAI, Google Gemini, Cohere, etc. are prohibited.
>
> Full build specification (step-by-step implementation details, SQL schema, prompt templates) is in [BUILD_SPEC.md](BUILD_SPEC.md).

---

## Common commands

```bash
# Install dependencies (editable + dev extras)
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_parser.py -v

# Process a resume (full pipeline)
python -m src.main process --file ./sample_resume.pdf

# Dry run (skip DB insert)
python -m src.main process --file ./sample_resume.pdf --dry-run

# Apply DB schema
psql $DATABASE_URL -f sql/schema.sql

# Start Ollama server (required before processing)
ollama serve

# Pull default model (one-time)
ollama pull mistral
```

---

## Architecture

The pipeline is a linear, single-command CLI with four independent modules wired together in `src/main.py`:

```
resume file → parser.py → extractor.py → validator.py → db.py
                                              ↓
                                         output/*.json
```

| Module | Responsibility |
|---|---|
| `parser.py` | `extract_text(file_path)` — PDF/DOCX/TXT → raw string |
| `extractor.py` | `extract_candidate(raw_text)` — Ollama chat → raw dict |
| `validator.py` | `validate(data)` — Pydantic parse + field normalisation → `CandidateSchema` |
| `db.py` | `insert_candidate(...)` — writes to `candidates` + `resumes` tables atomically |
| `models.py` | `CandidateSchema` Pydantic model (single source of truth for the schema) |
| `main.py` | Typer CLI; orchestrates the pipeline; handles `--dry-run` and `--output-dir` |

**Database:** SQLAlchemy 2.x. Postgres in production (`TEXT[]`, `JSONB`, `UUID`); SQLite in local dev — detected from `DATABASE_URL` prefix. Schema in `sql/schema.sql`. Two tables: `candidates` (flat fields) and `resumes` (FK to candidate, stores `education`/`experience`/`certifications` as JSONB, plus `raw_text` and `json_path`).

**Ollama integration:** `ollama.chat()` with `format="json"` (structured output mode). Model is always read from `OLLAMA_MODEL` env var (default: `mistral`). Never hardcode a model name.

**Output files:** JSON dumped to `OUTPUT_DIR` (default `./output/`). Filename: `candidate_{uuid4_short}.json`. Directory is created automatically if absent.

---

## Environment variables

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
DATABASE_URL=sqlite:///./dev.db   # or postgresql://...
OUTPUT_DIR=./output
```

Copy `.env.example` → `.env`. No API keys required.

---

## Code quality standards

- `from __future__ import annotations` at the top of every file.
- Google-style docstrings on every public module, class, and function.
- `logger = logging.getLogger(__name__)` per module; no `print()` for operational output.
- Specific exception types only — no bare `except`.
- All DB writes use `with session.begin():` for automatic rollback.
- All paths via `pathlib.Path` — no string concatenation.
- Constants (table names, model defaults, retry counts) as module-level names — no inline magic strings.
- Functions ≤ ~30 lines; single responsibility.
- `KeyboardInterrupt` caught in CLI; exits non-zero without traceback.
- Mutable default arguments forbidden — use `None` and assign in body.

---

## Testing

- Mock the Ollama client in `test_extractor.py` — no real LLM calls in tests.
- Sample resume fixture lives at `tests/fixtures/sample_resume.txt`.
- Each module (`parser`, `extractor`, `validator`, `db`) has its own test file.
