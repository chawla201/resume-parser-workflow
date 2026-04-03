"""Database writer: persists candidate and resume records via SQLAlchemy ORM."""

from __future__ import annotations

import json
import logging
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

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
