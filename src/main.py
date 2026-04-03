"""CLI entry point for the resume parser workflow."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import typer
from dotenv import load_dotenv

from src.logging_config import configure_logging

load_dotenv()
configure_logging()

logger = logging.getLogger(__name__)

app = typer.Typer(add_completion=False)

DEFAULT_OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")
UUID_SHORT_LENGTH: int = 8


@app.command()
def process(
    file: Path = typer.Option(..., "--file", help="Path to the resume file (PDF, DOCX, or TXT)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip database insert; write JSON only."),
    output_dir: Path = typer.Option(
        Path(DEFAULT_OUTPUT_DIR),
        "--output-dir",
        help="Directory to write JSON output files.",
    ),
) -> None:
    """Parse a resume file and persist structured candidate data.

    Runs the full pipeline: text extraction → LLM extraction → validation →
    JSON output → database insert (unless --dry-run is specified).

    Args:
        file: Path to the input resume file.
        dry_run: When True, skip the database insert step.
        output_dir: Directory for JSON output files.
    """
    from src.db import insert_candidate
    from src.extractor import extract_candidate
    from src.parser import extract_text
    from src.validator import validate

    try:
        logger.info("Step 1/5 — Extracting text from %s", file)
        raw_text = extract_text(str(file))
        if not raw_text.strip():
            raise ValueError("Extracted text is empty — file may be blank or image-only.")

        logger.info("Step 2/5 — Sending text to LLM")
        raw_dict = extract_candidate(raw_text)

        logger.info("Step 3/5 — Validating extracted data")
        candidate = validate(raw_dict)

        logger.info("Step 4/5 — Writing JSON to disk")
        json_path = _write_json(candidate, output_dir)

        if dry_run:
            logger.info("Dry run complete — skipping database insert.")
            typer.echo(f"Dry run complete. JSON written to: {json_path}")
            raise typer.Exit(0)

        logger.info("Step 5/5 — Inserting into database")
        candidate_id = insert_candidate(
            candidate=candidate,
            source_filename=file.name,
            json_path=str(json_path),
            raw_text=raw_text,
        )

        typer.echo(
            f"Success — candidate '{candidate.full_name}' saved.\n"
            f"  Candidate ID : {candidate_id}\n"
            f"  JSON output  : {json_path}"
        )

    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        raise typer.Exit(1)
    except (ValueError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    except (ConnectionError, RuntimeError) as exc:
        logger.error("%s", exc)
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


def _write_json(candidate: object, output_dir: Path) -> Path:
    """Serialise a validated candidate to a JSON file in *output_dir*.

    Args:
        candidate: A validated CandidateSchema instance.
        output_dir: Directory where the JSON file should be written.

    Returns:
        Path to the written JSON file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    short_id = str(uuid.uuid4())[:UUID_SHORT_LENGTH]
    filename = f"candidate_{short_id}.json"
    output_path = output_dir / filename
    output_path.write_text(candidate.model_dump_json(indent=2), encoding="utf-8")  # type: ignore[attr-defined]
    logger.info("JSON written to %s", output_path)
    return output_path


if __name__ == "__main__":
    app()
