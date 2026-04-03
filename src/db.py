"""Database writer: persists candidate and resume records via SQLAlchemy ORM."""

from __future__ import annotations

import json
import logging
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker, Session, selectinload

from src.models import CandidateSchema
from src.orm_models import CandidateRow, ResumeRow

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
_IS_SQLITE: bool = DATABASE_URL.startswith("sqlite")

_engine = create_engine(DATABASE_URL, future=True)
_SessionFactory: sessionmaker[Session] = sessionmaker(bind=_engine, future=True)


def insert_candidate(
    candidate: CandidateSchema,
    source_filename: str,
    json_path: str,
    raw_text: str,
) -> str:
    """Persist a validated candidate and their resume to the database.

    Inserts one row into ``candidates`` and one row into ``resumes`` within a
    single transaction using SQLAlchemy ORM. Both inserts succeed or both are
    rolled back automatically via the session context manager.

    Args:
        candidate: Validated candidate data.
        source_filename: Original filename of the uploaded resume.
        json_path: Path where the JSON output file was written.
        raw_text: Plain-text content of the resume.

    Returns:
        The UUID of the newly created ``candidates`` row as a string.

    Raises:
        RuntimeError: If the database transaction fails.
    """
    candidate_id = str(uuid.uuid4())
    resume_id = str(uuid.uuid4())

    candidate_row = CandidateRow(
        id=candidate_id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
        linkedin_url=candidate.linkedin_url,
        github_url=candidate.github_url,
        summary=candidate.summary,
        skills=_serialise_array(candidate.skills),
        languages=_serialise_array(candidate.languages),
    )

    resume_row = ResumeRow(
        id=resume_id,
        candidate_id=candidate_id,
        raw_text=raw_text,
        source_filename=source_filename,
        json_path=json_path,
        education=_serialise_json([e.model_dump() for e in candidate.education]),
        experience=_serialise_json([e.model_dump() for e in candidate.experience]),
        certifications=_serialise_json([c.model_dump() for c in candidate.certifications]),
    )

    try:
        with _SessionFactory() as session:
            with session.begin():
                session.add(candidate_row)
                session.add(resume_row)
    except Exception as exc:
        logger.exception("Database insert failed for candidate '%s'", candidate.full_name)
        raise RuntimeError(f"Failed to persist candidate to database: {exc}") from exc

    logger.info("Inserted candidate '%s' with id=%s", candidate.full_name, candidate_id)
    return candidate_id


def get_candidate(candidate_id: str) -> CandidateRow | None:
    """Retrieve a candidate row by its UUID.

    Args:
        candidate_id: UUID string of the candidate to look up.

    Returns:
        The :class:`CandidateRow` instance if found, otherwise ``None``.

    Raises:
        RuntimeError: If the database query fails.
    """
    try:
        with _SessionFactory() as session:
            return session.get(CandidateRow, candidate_id)
    except Exception as exc:
        logger.exception("Failed to retrieve candidate id=%s", candidate_id)
        raise RuntimeError(f"Failed to query candidate from database: {exc}") from exc


def get_candidate_with_resume(
    candidate_id: str,
) -> tuple[CandidateRow, ResumeRow | None] | None:
    """Retrieve a candidate row and its first associated resume by UUID.

    Args:
        candidate_id: UUID string of the candidate to look up.

    Returns:
        A tuple of ``(CandidateRow, ResumeRow | None)`` if found, else ``None``.

    Raises:
        RuntimeError: If the database query fails.
    """
    try:
        with _SessionFactory() as session:
            stmt = (
                select(CandidateRow)
                .options(selectinload(CandidateRow.resumes))
                .where(CandidateRow.id == candidate_id)
            )
            row = session.execute(stmt).scalars().first()
            if row is None:
                return None
            resume = row.resumes[0] if row.resumes else None
            # Detach from session by expunging so attributes remain accessible
            session.expunge_all()
            return row, resume
    except Exception as exc:
        logger.exception("Failed to retrieve candidate id=%s", candidate_id)
        raise RuntimeError(f"Failed to query candidate from database: {exc}") from exc


def list_candidates(
    limit: int = 20,
    offset: int = 0,
) -> list[tuple[CandidateRow, ResumeRow | None]]:
    """Return a paginated list of candidates with their first resume.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        List of ``(CandidateRow, ResumeRow | None)`` tuples ordered by
        ``created_at`` descending.

    Raises:
        RuntimeError: If the database query fails.
    """
    try:
        with _SessionFactory() as session:
            stmt = (
                select(CandidateRow)
                .options(selectinload(CandidateRow.resumes))
                .order_by(CandidateRow.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = session.execute(stmt).scalars().all()
            result = [(row, row.resumes[0] if row.resumes else None) for row in rows]
            session.expunge_all()
            return result
    except Exception as exc:
        logger.exception("Failed to list candidates")
        raise RuntimeError(f"Failed to list candidates from database: {exc}") from exc


def count_candidates() -> int:
    """Return the total number of candidate records.

    Returns:
        Integer count of all rows in the ``candidates`` table.

    Raises:
        RuntimeError: If the database query fails.
    """
    try:
        with _SessionFactory() as session:
            total = session.execute(select(func.count()).select_from(CandidateRow)).scalar_one()
            return int(total)
    except Exception as exc:
        logger.exception("Failed to count candidates")
        raise RuntimeError(f"Failed to count candidates in database: {exc}") from exc


def _deserialise_array(value: object) -> list[str]:
    """Deserialise an array value from storage.

    Converts a JSON string (SQLite) or native list (Postgres) to a Python list.

    Args:
        value: A JSON string or list of strings, or ``None``.

    Returns:
        A list of strings. Returns an empty list if value is ``None`` or empty.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _deserialise_json(value: object) -> list:
    """Deserialise a JSON value from storage.

    Converts a JSON string (SQLite) or native object (Postgres) to a Python object.

    Args:
        value: A JSON string or already-parsed object, or ``None``.

    Returns:
        Parsed Python object, or an empty list if value is ``None``.
    """
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _serialise_array(values: list[str]) -> object:
    """Serialise a list of strings for storage.

    Returns a JSON string for SQLite or the original list for Postgres.

    Args:
        values: List of string values to serialise.

    Returns:
        JSON string (SQLite) or the original list (Postgres).
    """
    if _IS_SQLITE:
        return json.dumps(values)
    return values


def _serialise_json(value: object) -> object:
    """Serialise a JSON-serialisable value for storage.

    Returns a JSON string for SQLite or the original object for Postgres.

    Args:
        value: A JSON-serialisable Python object.

    Returns:
        JSON string (SQLite) or the original object (Postgres).
    """
    if _IS_SQLITE:
        return json.dumps(value)
    return value
