"""LLM extractor: sends resume text to Ollama and returns a structured dict."""

from __future__ import annotations

import json
import logging
import os

import ollama
import tenacity

logger = logging.getLogger(__name__)

OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
RETRY_ATTEMPTS: int = int(os.getenv("OLLAMA_RETRY_ATTEMPTS", "3"))
RETRY_WAIT_BASE: float = float(os.getenv("OLLAMA_RETRY_WAIT_BASE", "2.0"))

SYSTEM_PROMPT: str = (
    "You are a resume parser. Extract structured information from the resume text provided. "
    "Return ONLY a valid JSON object — no markdown fences, no explanation, no preamble. "
    "Follow the schema exactly. If a field is not present in the resume, use null."
)

USER_PROMPT_TEMPLATE: str = """\
Extract all candidate information from this resume and return a JSON object with this exact schema:

{{
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
    {{
      "institution": "string",
      "degree": "string or null",
      "field_of_study": "string or null",
      "start_year": "int or null",
      "end_year": "int or null"
    }}
  ],
  "experience": [
    {{
      "company": "string",
      "title": "string",
      "location": "string or null",
      "start_date": "YYYY-MM or null",
      "end_date": "YYYY-MM or null",
      "is_current": "bool",
      "description": "string or null"
    }}
  ],
  "certifications": [
    {{
      "name": "string",
      "issuer": "string or null",
      "year": "int or null"
    }}
  ]
}}

Resume:
{raw_text}"""


def _log_retry_attempt(retry_state: tenacity.RetryCallState) -> None:
    """Log a warning each time a retryable call fails and will be retried.

    Args:
        retry_state: Tenacity state object containing attempt number and exception.
    """
    attempt = retry_state.attempt_number
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Ollama call failed (attempt %d/%d): %s — retrying...",
        attempt,
        RETRY_ATTEMPTS,
        exc,
    )


def extract_candidate(raw_text: str) -> dict:
    """Send resume text to the local Ollama model and return parsed candidate data.

    Retries up to ``RETRY_ATTEMPTS`` times on transient ``ConnectionError``
    failures using exponential backoff (base: ``RETRY_WAIT_BASE`` seconds).

    Args:
        raw_text: Plain-text content of the resume.

    Returns:
        Dictionary matching the candidate JSON schema.

    Raises:
        ConnectionError: If the Ollama server is unreachable after all retries.
        ValueError: If the model is not available or the response cannot be parsed.
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(raw_text=raw_text)
    logger.info("Sending resume to Ollama model '%s'", OLLAMA_MODEL)
    response = _call_ollama_with_retry(user_prompt)
    return _parse_response(response)


@tenacity.retry(
    retry=tenacity.retry_if_exception_type(ConnectionError),
    stop=tenacity.stop_after_attempt(RETRY_ATTEMPTS),
    wait=tenacity.wait_exponential(multiplier=RETRY_WAIT_BASE, min=RETRY_WAIT_BASE, max=30),
    before_sleep=_log_retry_attempt,
    reraise=True,
)
def _call_ollama_with_retry(user_prompt: str) -> object:
    """Call ``ollama.chat()`` with retry on transient connection failures.

    Args:
        user_prompt: Fully rendered user prompt string including resume text.

    Returns:
        Raw Ollama response object.

    Raises:
        ConnectionError: If the Ollama server cannot be reached.
        ValueError: If the model is not found (not retried).
    """
    try:
        return ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            format="json",
        )
    except ollama.ResponseError as exc:
        logger.exception("Ollama model error for model '%s'", OLLAMA_MODEL)
        if "not found" in str(exc).lower() or "pull" in str(exc).lower():
            raise ValueError(
                f"Model '{OLLAMA_MODEL}' not found. Run `ollama pull {OLLAMA_MODEL}`."
            ) from exc
        raise
    except Exception as exc:
        logger.exception("Failed to reach Ollama server at %s", OLLAMA_BASE_URL)
        raise ConnectionError(
            f"Ollama server not reachable at {OLLAMA_BASE_URL}. Run `ollama serve`."
        ) from exc


def _parse_response(response: object) -> dict:
    """Extract and JSON-decode the content from an Ollama chat response.

    Args:
        response: Raw response object returned by ``ollama.chat()``.

    Returns:
        Decoded dictionary from the model's JSON output.

    Raises:
        ValueError: If the response content cannot be decoded as JSON.
    """
    raw_content: str = response["message"]["content"]  # type: ignore[index]
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to parse LLM response as JSON. Raw content:\n%s", raw_content)
        raise ValueError(
            f"LLM returned invalid JSON. Raw response logged above. Error: {exc}"
        ) from exc
