"""Tests for src.db — database insert logic (uses in-memory SQLite via ORM)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set SQLite env before importing ORM models so _IS_SQLITE is evaluated correctly
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from src.models import CandidateSchema, Certification, Education, Experience  # noqa: E402
from src.orm_models import Base  # noqa: E402

SAMPLE_CANDIDATE: CandidateSchema = CandidateSchema(
    full_name="Jane Doe",
    email="jane.doe@example.com",
    phone="+1 415 555 0198",
    location="San Francisco, CA",
    skills=["Python", "Go"],
    languages=["English"],
    education=[
        Education(
            institution="UC Berkeley",
            degree="B.S.",
            field_of_study="Computer Science",
            start_year=2014,
            end_year=2018,
        )
    ],
    experience=[
        Experience(
            company="Acme Corp",
            title="Senior Software Engineer",
            start_date="2021-03",
            is_current=True,
        )
    ],
    certifications=[
        Certification(name="AWS SAA", issuer="Amazon Web Services", year=2022)
    ],
)


@pytest.fixture()
def in_memory_db():
    """Provide a patched in-memory SQLite engine using ORM metadata for schema creation."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, future=True)

    with (
        patch("src.db._engine", engine),
        patch("src.db._SessionFactory", factory),
        patch("src.db._IS_SQLITE", True),
    ):
        yield engine


def test_insert_candidate_returns_string_id(in_memory_db) -> None:
    """insert_candidate should return a non-empty 36-character UUID string."""
    from src.db import insert_candidate

    result = insert_candidate(
        candidate=SAMPLE_CANDIDATE,
        source_filename="resume.txt",
        json_path="/tmp/candidate_abc.json",
        raw_text="Jane Doe resume text",
    )
    assert isinstance(result, str)
    assert len(result) == 36


def test_insert_candidate_persists_to_candidates_table(in_memory_db) -> None:
    """insert_candidate should create a row in the candidates table."""
    from src.db import insert_candidate

    candidate_id = insert_candidate(
        candidate=SAMPLE_CANDIDATE,
        source_filename="resume.txt",
        json_path="/tmp/candidate_abc.json",
        raw_text="Jane Doe resume text",
    )

    with in_memory_db.connect() as conn:
        row = conn.execute(
            text("SELECT full_name, email FROM candidates WHERE id = :id"),
            {"id": candidate_id},
        ).fetchone()

    assert row is not None
    assert row[0] == "Jane Doe"
    assert row[1] == "jane.doe@example.com"


def test_insert_candidate_persists_to_resumes_table(in_memory_db) -> None:
    """insert_candidate should create a linked row in the resumes table."""
    from src.db import insert_candidate

    candidate_id = insert_candidate(
        candidate=SAMPLE_CANDIDATE,
        source_filename="resume.txt",
        json_path="/tmp/candidate_abc.json",
        raw_text="Jane Doe resume text",
    )

    with in_memory_db.connect() as conn:
        row = conn.execute(
            text("SELECT candidate_id, source_filename FROM resumes WHERE candidate_id = :cid"),
            {"cid": candidate_id},
        ).fetchone()

    assert row is not None
    assert row[0] == candidate_id
    assert row[1] == "resume.txt"


def test_get_candidate_returns_row_after_insert(in_memory_db) -> None:
    """get_candidate should retrieve the candidate inserted by insert_candidate."""
    from src.db import get_candidate, insert_candidate

    candidate_id = insert_candidate(
        candidate=SAMPLE_CANDIDATE,
        source_filename="resume.txt",
        json_path="/tmp/candidate_abc.json",
        raw_text="Jane Doe resume text",
    )

    row = get_candidate(candidate_id)

    assert row is not None
    assert row.full_name == "Jane Doe"
    assert row.email == "jane.doe@example.com"


def test_get_candidate_returns_none_for_unknown_id(in_memory_db) -> None:
    """get_candidate should return None when the ID does not exist."""
    from src.db import get_candidate

    result = get_candidate("00000000-0000-0000-0000-000000000000")
    assert result is None
