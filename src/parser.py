"""Document parser: converts PDF, DOCX, and TXT resume files to plain text."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})
WHITESPACE_PATTERN: re.Pattern[str] = re.compile(r"\n{3,}")
MAX_FILE_SIZE_BYTES: int = int(os.getenv("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB


def extract_text(file_path: str) -> str:
    """Extract plain text from a PDF, DOCX, or TXT resume file.

    Args:
        file_path: Absolute or relative path to the resume file.

    Returns:
        Cleaned plain-text content of the resume.

    Raises:
        FileNotFoundError: If the file does not exist at *file_path*.
        ValueError: If the file extension is unsupported or the file exceeds
            ``MAX_FILE_SIZE_BYTES``.
        PermissionError: If *file_path* is a symlink resolving outside the
            expected filesystem boundary (non-regular file).
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")
    if not path.is_file():
        raise PermissionError(f"Path is not a regular file: {path}")

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size {file_size:,} bytes exceeds maximum allowed "
            f"{MAX_FILE_SIZE_BYTES:,} bytes ({MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB)."
        )

    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{extension}'. "
            f"Supported formats: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    logger.info("Extracting text from %s (%d bytes)", path, file_size)

    if extension == ".pdf":
        raw_text = _extract_from_pdf(path)
    elif extension == ".docx":
        raw_text = _extract_from_docx(path)
    else:
        raw_text = _extract_from_txt(path)

    return _normalise_whitespace(raw_text)


def _extract_from_pdf(path: Path) -> str:
    """Read all pages of a PDF and concatenate their text.

    Args:
        path: Path to the PDF file.

    Returns:
        Raw concatenated text from every page.
    """
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
    return "\n".join(pages)


def _extract_from_docx(path: Path) -> str:
    """Read all paragraphs from a DOCX file.

    Args:
        path: Path to the DOCX file.

    Returns:
        Raw concatenated paragraph text.
    """
    document = Document(str(path))
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def _extract_from_txt(path: Path) -> str:
    """Read a plain-text file encoded in UTF-8.

    Args:
        path: Path to the TXT file.

    Returns:
        File contents as a string.
    """
    return path.read_text(encoding="utf-8")


def _normalise_whitespace(text: str) -> str:
    """Collapse runs of three or more consecutive newlines to two.

    Args:
        text: Raw text that may contain excessive blank lines.

    Returns:
        Text with normalised whitespace.
    """
    return WHITESPACE_PATTERN.sub("\n\n", text).strip()
