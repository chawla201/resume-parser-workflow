-- Resume parser workflow — database schema
-- Run against Postgres: psql $DATABASE_URL -f sql/schema.sql
-- For SQLite dev mode use the SQLAlchemy layer in src/db.py directly;
-- TEXT[] and JSONB columns are handled transparently there.

CREATE TABLE IF NOT EXISTS candidates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name     TEXT NOT NULL,
    email         TEXT,
    phone         TEXT,
    location      TEXT,
    linkedin_url  TEXT,
    github_url    TEXT,
    summary       TEXT,
    skills        TEXT[],
    languages     TEXT[],
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resumes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    raw_text        TEXT,
    source_filename TEXT,
    json_path       TEXT,
    education       JSONB,
    experience      JSONB,
    certifications  JSONB,
    parsed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_candidate_id ON resumes(candidate_id);
