"""Tests for src.api — FastAPI endpoints (Ollama and DB are mocked)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import app

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"
SAMPLE_RESUME: Path = FIXTURES_DIR / "sample_resume.txt"

SAMPLE_CANDIDATE_DICT: dict = {
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "+1 415 555 0198",
    "location": "San Francisco, CA",
    "linkedin_url": None,
    "github_url": None,
    "summary": None,
    "skills": ["Python"],
    "languages": ["English"],
    "education": [],
    "experience": [],
    "certifications": [],
}


@pytest.fixture()
def client() -> TestClient:
    """Return a synchronous TestClient for the FastAPI app."""
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_returns_200(client: TestClient) -> None:
    """GET /health should always return HTTP 200."""
    with patch("src.api._check_ollama", return_value=True), patch(
        "src.api._check_db", return_value=True
    ):
        response = client.get("/health")
    assert response.status_code == 200


def test_health_status_ok_when_all_up(client: TestClient) -> None:
    """GET /health should report status='ok' when both Ollama and DB are up."""
    with patch("src.api._check_ollama", return_value=True), patch(
        "src.api._check_db", return_value=True
    ):
        data = client.get("/health").json()
    assert data["status"] == "ok"
    assert data["ollama"] is True
    assert data["db"] is True


def test_health_status_degraded_when_ollama_down(client: TestClient) -> None:
    """GET /health should report status='degraded' when Ollama is unreachable."""
    with patch("src.api._check_ollama", return_value=False), patch(
        "src.api._check_db", return_value=True
    ):
        data = client.get("/health").json()
    assert data["status"] == "degraded"
    assert data["ollama"] is False


# ---------------------------------------------------------------------------
# POST /api/v1/parse
# ---------------------------------------------------------------------------


@patch("src.api.insert_candidate", return_value="candidate-uuid-1234")
@patch("src.api.validate")
@patch("src.api.extract_candidate", return_value=SAMPLE_CANDIDATE_DICT)
@patch("src.api.extract_text", return_value="Jane Doe resume text here")
def test_parse_returns_200_for_txt(
    mock_extract_text: MagicMock,
    mock_extract_candidate: MagicMock,
    mock_validate: MagicMock,
    mock_insert: MagicMock,
    client: TestClient,
) -> None:
    """POST /api/v1/parse should return 200 with candidate data for a TXT file."""
    mock_validate.return_value = MagicMock(
        full_name="Jane Doe",
        model_dump=lambda: SAMPLE_CANDIDATE_DICT,
        model_dump_json=lambda indent: json.dumps(SAMPLE_CANDIDATE_DICT, indent=indent),
    )
    with SAMPLE_RESUME.open("rb") as f:
        response = client.post("/api/v1/parse", files={"file": ("resume.txt", f, "text/plain")})
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_id"] == "candidate-uuid-1234"
    assert data["dry_run"] is False


@patch("src.api.extract_text", return_value="Jane Doe resume text here")
@patch("src.api.extract_candidate", return_value=SAMPLE_CANDIDATE_DICT)
@patch("src.api.validate")
def test_parse_dry_run_skips_db_insert(
    mock_validate: MagicMock,
    mock_extract_candidate: MagicMock,
    mock_extract_text: MagicMock,
    client: TestClient,
) -> None:
    """POST /api/v1/parse?dry_run=true should skip DB insert and return null candidate_id."""
    mock_validate.return_value = MagicMock(
        full_name="Jane Doe",
        model_dump=lambda: SAMPLE_CANDIDATE_DICT,
        model_dump_json=lambda indent: json.dumps(SAMPLE_CANDIDATE_DICT, indent=indent),
    )
    with SAMPLE_RESUME.open("rb") as f:
        response = client.post(
            "/api/v1/parse?dry_run=true",
            files={"file": ("resume.txt", f, "text/plain")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_id"] is None
    assert data["dry_run"] is True


def test_parse_rejects_unsupported_extension(client: TestClient) -> None:
    """POST /api/v1/parse should return 400 for unsupported file extensions."""
    response = client.post(
        "/api/v1/parse",
        files={"file": ("resume.xyz", b"content", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@patch("src.api.extract_text", return_value="   ")
def test_parse_returns_400_for_empty_text(
    mock_extract_text: MagicMock,
    client: TestClient,
) -> None:
    """POST /api/v1/parse should return 400 when extracted text is empty."""
    with SAMPLE_RESUME.open("rb") as f:
        response = client.post("/api/v1/parse", files={"file": ("resume.txt", f, "text/plain")})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@patch("src.api.extract_text", return_value="Jane Doe resume text")
@patch("src.api.extract_candidate", side_effect=ConnectionError("Ollama not reachable"))
def test_parse_returns_502_when_ollama_down(
    mock_extract_candidate: MagicMock,
    mock_extract_text: MagicMock,
    client: TestClient,
) -> None:
    """POST /api/v1/parse should return 502 when Ollama is unreachable."""
    with SAMPLE_RESUME.open("rb") as f:
        response = client.post("/api/v1/parse", files={"file": ("resume.txt", f, "text/plain")})
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/v1/candidates/{id}
# ---------------------------------------------------------------------------


@patch("src.api._get_candidate")
def test_get_candidate_returns_200_when_found(
    mock_get: MagicMock,
    client: TestClient,
) -> None:
    """GET /api/v1/candidates/{id} should return 200 when the candidate exists."""
    mock_row = MagicMock()
    mock_row.id = "abc-123"
    mock_row.full_name = "Jane Doe"
    mock_row.email = "jane@example.com"
    mock_row.phone = None
    mock_row.location = None
    mock_row.linkedin_url = None
    mock_row.github_url = None
    mock_row.summary = None
    mock_get.return_value = mock_row

    response = client.get("/api/v1/candidates/abc-123")
    assert response.status_code == 200
    assert response.json()["full_name"] == "Jane Doe"


@patch("src.api._get_candidate", return_value=None)
def test_get_candidate_returns_404_when_missing(
    mock_get: MagicMock,
    client: TestClient,
) -> None:
    """GET /api/v1/candidates/{id} should return 404 when the candidate does not exist."""
    response = client.get("/api/v1/candidates/nonexistent-id")
    assert response.status_code == 404
