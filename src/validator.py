"""Validator: parses and normalises raw LLM output into a CandidateSchema instance."""

from __future__ import annotations

import logging
import re

from pydantic import ValidationError

from src.models import CandidateSchema

logger = logging.getLogger(__name__)

PHONE_STRIP_PATTERN: re.Pattern[str] = re.compile(r"[^\d+\s]")


def validate(data: dict) -> CandidateSchema:
    """Validate and normalise a raw candidate dictionary against CandidateSchema.

    Normalisation rules applied before Pydantic parsing:
    - Email is lowercased.
    - Phone is stripped of all characters except digits, ``+``, and spaces.

    Args:
        data: Raw dictionary produced by the LLM extractor.

    Returns:
        A fully validated :class:`CandidateSchema` instance.

    Raises:
        ValueError: If the data does not conform to the schema, with field-level
            error details logged before raising.
    """
    normalised = _normalise_fields(data)

    try:
        return CandidateSchema.model_validate(normalised)
    except ValidationError as exc:
        logger.exception("Pydantic validation failed. Field errors:\n%s", exc)
        raise ValueError(f"Candidate data failed schema validation: {exc}") from exc


def _normalise_fields(data: dict) -> dict:
    """Apply field-level normalisation to a raw candidate dictionary.

    Args:
        data: Raw dictionary, potentially with un-normalised field values.

    Returns:
        A shallow copy of *data* with normalised ``email`` and ``phone`` fields.
    """
    normalised = dict(data)

    if email := normalised.get("email"):
        normalised["email"] = str(email).lower().strip()

    if phone := normalised.get("phone"):
        normalised["phone"] = PHONE_STRIP_PATTERN.sub("", str(phone)).strip()

    return normalised
