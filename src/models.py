"""Pydantic models defining the canonical candidate schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Education(BaseModel):
    """A single education entry on a resume.

    Attributes:
        institution: Name of the educational institution.
        degree: Degree type (e.g. Bachelor of Science).
        field_of_study: Major or area of study.
        start_year: Year enrolment began.
        end_year: Year of graduation or expected graduation.
    """

    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None


class Experience(BaseModel):
    """A single work-experience entry on a resume.

    Attributes:
        company: Employer name.
        title: Job title held.
        location: Office or remote location.
        start_date: First month of employment in YYYY-MM format.
        end_date: Last month of employment in YYYY-MM format, or None if current.
        is_current: True when the candidate is still in this role.
        description: Freeform role description or bullet-point summary.
    """

    company: str
    title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None


class Certification(BaseModel):
    """A professional certification or credential.

    Attributes:
        name: Full certification name.
        issuer: Issuing body or organisation.
        year: Year the certification was awarded.
    """

    name: str
    issuer: str | None = None
    year: int | None = None


class CandidateSchema(BaseModel):
    """Top-level model representing all structured data extracted from a resume.

    Attributes:
        full_name: Candidate's full legal name.
        email: Primary contact email address.
        phone: Contact phone number.
        location: City, state, country, or remote indication.
        linkedin_url: URL to the candidate's LinkedIn profile.
        github_url: URL to the candidate's GitHub profile.
        summary: Professional summary or objective statement.
        skills: List of technical or professional skills.
        languages: Spoken or programming languages the candidate knows.
        education: Ordered list of education entries (most recent first).
        experience: Ordered list of work-experience entries (most recent first).
        certifications: List of professional certifications.
    """

    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
