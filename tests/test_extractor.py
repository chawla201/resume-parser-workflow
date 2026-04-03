"""Tests for src.extractor — Ollama LLM extraction (Ollama client is mocked)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.extractor import extract_candidate

SAMPLE_CANDIDATE_DICT: dict = {
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "+1 415 555 0198",
    "location": "San Francisco, CA",
    "linkedin_url": "linkedin.com/in/janedoe",
    "github_url": "github.com/janedoe",
    "summary": "Senior software engineer with 8 years of experience.",
    "skills": ["Python", "Go", "Kubernetes"],
    "languages": ["English", "Spanish"],
    "education": [
        {
            "institution": "UC Berkeley",
            "degree": "B.S.",
            "field_of_study": "Computer Science",
            "start_year": 2014,
            "end_year": 2018,
        }
    ],
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Senior Software Engineer",
            "location": "San Francisco, CA",
            "start_date": "2021-03",
            "end_date": None,
            "is_current": True,
            "description": "Led re-architecture of the payments service.",
        }
    ],
    "certifications": [
        {"name": "AWS Certified Solutions Architect", "issuer": "Amazon Web Services", "year": 2022}
    ],
}


def _make_mock_response(content: dict) -> MagicMock:
    """Build a mock Ollama response object with the given content dict."""
    mock_response = MagicMock()
    mock_response.__getitem__ = lambda self, key: (
        {"message": MagicMock(__getitem__=lambda s, k: json.dumps(content) if k == "content" else None)}[key]
    )
    return mock_response


@patch("src.extractor.ollama.chat")
def test_extract_candidate_returns_dict(mock_chat: MagicMock) -> None:
    """extract_candidate should return a dict when Ollama responds with valid JSON."""
    mock_response = {"message": {"content": json.dumps(SAMPLE_CANDIDATE_DICT)}}
    mock_chat.return_value = mock_response

    result = extract_candidate("some resume text")

    assert isinstance(result, dict)
    assert result["full_name"] == "Jane Doe"
    mock_chat.assert_called_once()


@patch("src.extractor.ollama.chat")
def test_extract_candidate_passes_format_json(mock_chat: MagicMock) -> None:
    """extract_candidate must call ollama.chat with format='json'."""
    mock_response = {"message": {"content": json.dumps(SAMPLE_CANDIDATE_DICT)}}
    mock_chat.return_value = mock_response

    extract_candidate("some resume text")

    _, kwargs = mock_chat.call_args
    assert kwargs.get("format") == "json"


@patch("src.extractor.ollama.chat")
def test_extract_candidate_raises_on_invalid_json(mock_chat: MagicMock) -> None:
    """extract_candidate should raise ValueError when the LLM returns malformed JSON."""
    mock_response = {"message": {"content": "not valid json { broken"}}
    mock_chat.return_value = mock_response

    with pytest.raises(ValueError, match="invalid JSON"):
        extract_candidate("some resume text")


@patch("src.extractor.ollama.chat")
def test_extract_candidate_raises_connection_error_on_failure(mock_chat: MagicMock) -> None:
    """extract_candidate should raise ConnectionError when Ollama is unreachable."""
    mock_chat.side_effect = Exception("connection refused")

    with pytest.raises(ConnectionError, match="Ollama server not reachable"):
        extract_candidate("some resume text")


@patch("src.extractor.RETRY_ATTEMPTS", 3)
@patch("src.extractor.ollama.chat")
def test_extract_candidate_retries_on_connection_error(mock_chat: MagicMock) -> None:
    """extract_candidate should retry RETRY_ATTEMPTS times before raising ConnectionError."""
    mock_chat.side_effect = Exception("connection refused")

    with pytest.raises(ConnectionError):
        extract_candidate("some resume text")

    assert mock_chat.call_count == 3
