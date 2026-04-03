FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by pdfplumber / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only the package manifest first to leverage layer caching
COPY pyproject.toml .

# Install all runtime dependencies (no dev extras)
RUN pip install --no-cache-dir -e "."

# Copy application source
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
