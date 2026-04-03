"""Tests for src.parser — document text extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.parser import extract_text

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"
SAMPLE_RESUME: Path = FIXTURES_DIR / "sample_resume.txt"


def test_extract_text_from_txt_returns_string() -> None:
    """extract_text should return a non-empty string for a valid TXT file."""
    result = extract_text(str(SAMPLE_RESUME))
    assert isinstance(result, str)
    assert len(result) > 0


def test_extract_text_contains_expected_content() -> None:
    """Extracted text should contain known content from the sample resume."""
    result = extract_text(str(SAMPLE_RESUME))
    assert "Jane Doe" in result
    assert "jane.doe@example.com" in result


def test_extract_text_strips_excessive_whitespace() -> None:
    """Extracted text should not contain more than two consecutive newlines."""
    result = extract_text(str(SAMPLE_RESUME))
    assert "\n\n\n" not in result


def test_extract_text_raises_for_unsupported_format(tmp_path: Path) -> None:
    """extract_text should raise ValueError for unsupported file extensions."""
    bad_file = tmp_path / "resume.xyz"
    bad_file.write_text("dummy content", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file format"):
        extract_text(str(bad_file))


def test_extract_text_raises_for_missing_file() -> None:
    """extract_text should raise FileNotFoundError when the file does not exist."""
    with pytest.raises(FileNotFoundError):
        extract_text("/nonexistent/path/resume.txt")
