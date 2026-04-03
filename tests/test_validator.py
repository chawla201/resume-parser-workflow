"""Tests for src.validator — JSON schema validation and normalisation."""

from __future__ import annotations

import pytest

from src.models import CandidateSchema
from src.validator import validate

VALID_DATA: dict = {
    "full_name": "Jane Doe",
    "email": "Jane.Doe@Example.COM",
    "phone": "(415) 555-0198",
    "location": "San Francisco, CA",
    "linkedin_url": None,
    "github_url": None,
    "summary": None,
    "skills": ["Python", "Go"],
    "languages": ["English"],
    "education": [],
    "experience": [],
    "certifications": [],
}


def test_validate_returns_candidate_schema() -> None:
    """validate should return a CandidateSchema instance for valid input."""
    result = validate(VALID_DATA)
    assert isinstance(result, CandidateSchema)


def test_validate_normalises_email_to_lowercase() -> None:
    """validate should normalise email addresses to lowercase."""
    result = validate(VALID_DATA)
    assert result.email == "jane.doe@example.com"


def test_validate_strips_phone_punctuation() -> None:
    """validate should strip non-digit/non-plus/non-space chars from phone."""
    result = validate(VALID_DATA)
    assert result.phone == "415 5550198"


def test_validate_raises_for_missing_full_name() -> None:
    """validate should raise ValueError when full_name is missing."""
    bad_data = {k: v for k, v in VALID_DATA.items() if k != "full_name"}
    with pytest.raises(ValueError, match="validation"):
        validate(bad_data)


def test_validate_accepts_null_optional_fields() -> None:
    """validate should succeed when all optional fields are None."""
    minimal = {"full_name": "John Smith"}
    result = validate(minimal)
    assert result.full_name == "John Smith"
    assert result.email is None
    assert result.skills == []
