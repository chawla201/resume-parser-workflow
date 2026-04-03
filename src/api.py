"""FastAPI application exposing the resume parser pipeline over HTTP."""

from __future__ import annotations

import datetime
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

import ollama as ollama_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.db import insert_candidate
from src.extractor import extract_candidate
from src.logging_config import REQUEST_ID, configure_logging
from src.parser import extract_text
from src.validator import validate

load_dotenv()
configure_logging()

import logging  # noqa: E402 — must come after configure_logging()

logger = logging.getLogger(__name__)

OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./output"))
UUID_SHORT_LENGTH: int = 8
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})

app = FastAPI(
    title="Resume Parser API",
    version="1.0.0",
    description="Parse resumes with a local Ollama LLM and persist candidate data.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware: inject correlation ID into every request
# ---------------------------------------------------------------------------


@app.middleware("http")
async def _request_id_middleware(request: Request, call_next: Any) -> Any:
    """Attach a unique request_id to each request for log correlation.

    Args:
        request: Incoming HTTP request.
        call_next: Next middleware or route handler.

    Returns:
        HTTP response with ``X-Request-ID`` header set.
    """
    request_id = str(uuid.uuid4())
    token = REQUEST_ID.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        REQUEST_ID.reset(token)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", summary="Health check")
def health() -> dict[str, Any]:
    """Return service health including Ollama and database reachability.

    Returns:
        Dict with ``status``, ``ollama`` (bool), and ``db`` (bool) keys.
    """
    ollama_ok = _check_ollama()
    db_ok = _check_db()
    overall = "ok" if (ollama_ok and db_ok) else "degraded"
    return {"status": overall, "ollama": ollama_ok, "db": db_ok}


@app.post("/api/v1/parse", summary="Parse a resume file", status_code=status.HTTP_200_OK)
async def parse_resume(
    file: UploadFile,
    dry_run: bool = Query(False, description="Skip database insert when true."),
) -> JSONResponse:
    """Accept a resume file upload and run the full parsing pipeline.

    Args:
        file: Multipart-uploaded resume file (PDF, DOCX, or TXT).
        dry_run: When ``True``, skips the database insert step.

    Returns:
        JSON object containing ``candidate_id``, ``candidate`` data, and
        ``json_path`` of the written output file.

    Raises:
        HTTPException 400: If the file extension is not supported or extracted
            text is empty.
        HTTPException 502: If the Ollama server is unreachable.
        HTTPException 422: If LLM output fails schema validation.
        HTTPException 500: For unexpected internal errors.
    """
    filename = file.filename or "upload"
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{extension}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    logger.info("Received resume upload: %s", filename)

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(await file.read())

    try:
        raw_text = extract_text(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extracted text is empty — file may be blank or image-only.",
        )

    try:
        raw_dict = extract_candidate(raw_text)
    except ConnectionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        candidate = validate(raw_dict)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    json_path = _write_json_output(candidate)

    candidate_id: str | None = None
    if not dry_run:
        try:
            candidate_id = insert_candidate(
                candidate=candidate,
                source_filename=filename,
                json_path=str(json_path),
                raw_text=raw_text,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    logger.info("Parsed candidate '%s' (id=%s)", candidate.full_name, candidate_id)

    return JSONResponse(
        content={
            "candidate_id": candidate_id,
            "candidate": candidate.model_dump(),
            "json_path": str(json_path),
            "dry_run": dry_run,
        }
    )


@app.get("/api/v1/candidates", summary="List all parsed candidates")
def list_candidates(
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return."),
    offset: int = Query(0, ge=0, description="Number of records to skip."),
) -> JSONResponse:
    """Return a paginated list of candidates read from JSON files in OUTPUT_DIR.

    Args:
        limit: Maximum number of candidates to return (1–100).
        offset: Number of candidates to skip for pagination.

    Returns:
        JSON object with ``total``, ``limit``, ``offset``, and ``items`` list.
    """
    files = _sorted_output_files()
    total = len(files)
    page_files = files[offset : offset + limit]
    items = [d for f in page_files for d in [_read_json_file(f)] if d is not None]
    return JSONResponse(content={"total": total, "limit": limit, "offset": offset, "items": items})


@app.get("/api/v1/candidates/{candidate_id}", summary="Retrieve a candidate by ID")
def get_candidate(candidate_id: str) -> JSONResponse:
    """Fetch a candidate record by its file stem (e.g. ``candidate_abc12345``).

    Args:
        candidate_id: Stem of the JSON filename in OUTPUT_DIR.

    Returns:
        JSON object with all candidate fields.

    Raises:
        HTTPException 404: If no matching file exists.
    """
    json_file = OUTPUT_DIR / f"{candidate_id}.json"
    if not json_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found.",
        )
    data = _read_json_file(json_file)
    if data is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read candidate file.")
    return JSONResponse(content=data)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sorted_output_files() -> list[Path]:
    """Return all JSON files in OUTPUT_DIR sorted newest-first by modification time.

    Returns:
        List of Path objects for each ``.json`` file found.
    """
    if not OUTPUT_DIR.is_dir():
        return []
    files = list(OUTPUT_DIR.glob("*.json"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _read_json_file(path: Path) -> dict[str, Any] | None:
    """Parse a candidate JSON file and return a response-safe dict.

    The file stem is used as the ``id`` field; file modification time is used
    as ``parsed_at`` since it is not stored inside the JSON.

    Args:
        path: Path to a candidate JSON file.

    Returns:
        Dict with all candidate fields, or ``None`` if the file cannot be read.
    """
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not read or parse %s", path)
        return None
    mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.timezone.utc)
    data["id"] = path.stem
    data["parsed_at"] = mtime.isoformat()
    data["source_filename"] = path.name
    return data


def _write_json_output(candidate: Any) -> Path:
    """Write validated candidate data to a JSON file in OUTPUT_DIR.

    Args:
        candidate: A validated CandidateSchema instance.

    Returns:
        Path to the written JSON file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    short_id = str(uuid.uuid4())[:UUID_SHORT_LENGTH]
    output_path = OUTPUT_DIR / f"candidate_{short_id}.json"
    output_path.write_text(candidate.model_dump_json(indent=2), encoding="utf-8")
    logger.info("JSON written to %s", output_path)
    return output_path


def _check_ollama() -> bool:
    """Probe the Ollama server to verify it is reachable.

    Returns:
        ``True`` if the server responds, ``False`` otherwise.
    """
    try:
        ollama_sdk.list()
        return True
    except Exception:
        return False


def _check_db() -> bool:
    """Probe the database to verify the connection is healthy.

    Returns:
        ``True`` if a trivial query succeeds, ``False`` otherwise.
    """
    from sqlalchemy import text

    from src.db import _engine

    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
