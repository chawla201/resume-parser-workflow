# Resume Parser — User Guide

This guide walks you through setting up and using the Resume Parser from scratch. By the end, you will be able to upload a PDF resume and receive structured, machine-readable information extracted from it — no manual data entry required.

---

## What Does This Tool Do?

You upload a resume (PDF, Word document, or plain text file). The tool reads it, sends the text to a local AI model running on your machine, and returns structured data like this:

```json
{
  "full_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "phone": "+1 415 555 0198",
  "location": "San Francisco, CA",
  "skills": ["Python", "Go", "Kubernetes"],
  "education": [
    {
      "institution": "UC Berkeley",
      "degree": "B.S.",
      "field_of_study": "Computer Science",
      "start_year": 2014,
      "end_year": 2018
    }
  ],
  "experience": [
    {
      "company": "Acme Corp",
      "title": "Senior Software Engineer",
      "start_date": "2021-03",
      "is_current": true
    }
  ],
  "certifications": [
    {
      "name": "AWS Certified Solutions Architect",
      "issuer": "Amazon Web Services",
      "year": 2022
    }
  ]
}
```

All processing happens **on your machine**. No data is sent to any external service or cloud API.

---

## What You Need Before Starting

| Requirement | Why | Install link |
|---|---|---|
| **Docker Desktop** | Runs the application and database in isolated containers | https://www.docker.com/products/docker-desktop |
| **4 GB free disk space** | Stores the AI model (~4 GB for the default Mistral model) | — |
| **8 GB RAM** | Recommended for comfortable AI model inference | — |

That is all. Python, PostgreSQL, and the AI model are all handled automatically.

---

## Step 1 — Download the Project

If you have Git installed:

```bash
git clone <repository-url>
cd resume-parser-workflow
```

If not, download the ZIP from the repository page and unzip it, then open a terminal in that folder.

---

## Step 2 — Start All Services

Run this single command from inside the project folder:

```bash
docker compose up -d
```

This will:
1. Download the required Docker images (first run only — takes a few minutes)
2. Start a PostgreSQL database to store parsed results
3. Start an Ollama AI server for local inference
4. Build and start the resume parser API

To confirm everything is running:

```bash
docker compose ps
```

You should see three services: `postgres`, `ollama`, and `app`, all with status `running`.

---

## Step 3 — Download the AI Model (First Time Only)

The AI model that reads resumes must be downloaded once before you can parse anything:

```bash
docker compose exec ollama ollama pull mistral
```

This downloads the Mistral 7B model (~4 GB). It only needs to be done once — the model is saved to a persistent volume and survives container restarts.

---

## Step 4 — Verify the Service Is Ready

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "ollama": true, "db": true}
```

If you see `"ollama": false`, wait 30 seconds and try again — the model may still be loading. If you see `"db": false`, the database is still initialising; wait a few more seconds.

---

## Step 5 — Parse a Resume

### Using curl (terminal)

```bash
curl -X POST http://localhost:8000/api/v1/parse \
  -F "file=@/path/to/your/resume.pdf"
```

Replace `/path/to/your/resume.pdf` with the actual path to your file.

**Supported formats:** `.pdf`, `.docx`, `.txt`

### Using a REST client (e.g. Postman, Insomnia)

1. Create a new `POST` request to `http://localhost:8000/api/v1/parse`
2. Set the body type to **form-data**
3. Add a field named `file`, set its type to **File**, and select your resume
4. Send the request

### Example response

```json
{
  "candidate_id": "a3f8c2e1-4b5d-4f2a-9c1e-8d7b6a5f3e2c",
  "dry_run": false,
  "json_path": "/app/output/candidate_a3f8c2e1.json",
  "candidate": {
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "+1 415 555 0198",
    "location": "San Francisco, CA",
    "linkedin_url": "linkedin.com/in/janedoe",
    "github_url": "github.com/janedoe",
    "summary": "Senior software engineer with 8 years of experience...",
    "skills": ["Python", "Go", "Kubernetes", "PostgreSQL", "Docker"],
    "languages": ["English", "Spanish"],
    "education": [
      {
        "institution": "University of California, Berkeley",
        "degree": "B.S.",
        "field_of_study": "Computer Science",
        "start_year": 2014,
        "end_year": 2018
      }
    ],
    "experience": [
      {
        "company": "Acme Corp",
        "title": "Senior Software Engineer",
        "location": "San Francisco, CA",
        "start_date": "2021-03",
        "end_date": null,
        "is_current": true,
        "description": "Led re-architecture of the payments service..."
      }
    ],
    "certifications": [
      {
        "name": "AWS Certified Solutions Architect – Associate",
        "issuer": "Amazon Web Services",
        "year": 2022
      }
    ]
  }
}
```

The `candidate_id` is a unique identifier. Use it to retrieve this candidate's data later.

---

## Retrieving a Previously Parsed Resume

Every parsed resume is saved to the database. To look up a candidate by their ID:

```bash
curl http://localhost:8000/api/v1/candidates/a3f8c2e1-4b5d-4f2a-9c1e-8d7b6a5f3e2c
```

Response:

```json
{
  "id": "a3f8c2e1-4b5d-4f2a-9c1e-8d7b6a5f3e2c",
  "full_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "phone": "+1 415 555 0198",
  "location": "San Francisco, CA",
  "linkedin_url": "linkedin.com/in/janedoe",
  "github_url": "github.com/janedoe",
  "summary": "Senior software engineer with 8 years of experience..."
}
```

---

## Test Without Saving to Database (Dry Run)

If you want to see the extracted data without storing it, add `?dry_run=true`:

```bash
curl -X POST "http://localhost:8000/api/v1/parse?dry_run=true" \
  -F "file=@/path/to/your/resume.pdf"
```

The response is identical, but `candidate_id` will be `null` and nothing is written to the database.

---

## Understanding the Output Fields

| Field | Description | Example |
|---|---|---|
| `full_name` | Candidate's full name | `"Jane Doe"` |
| `email` | Email address | `"jane@example.com"` |
| `phone` | Phone number | `"+1 415 555 0198"` |
| `location` | City or region | `"San Francisco, CA"` |
| `linkedin_url` | LinkedIn profile URL | `"linkedin.com/in/janedoe"` |
| `github_url` | GitHub profile URL | `"github.com/janedoe"` |
| `summary` | Professional summary from the resume | `"8 years of experience..."` |
| `skills` | List of technical and soft skills | `["Python", "Docker"]` |
| `languages` | Spoken languages | `["English", "Spanish"]` |
| `education` | Degrees and institutions | See below |
| `experience` | Work history | See below |
| `certifications` | Professional credentials | See below |

### Education fields
| Field | Description |
|---|---|
| `institution` | University or school name |
| `degree` | Degree type (B.S., M.S., Ph.D., etc.) |
| `field_of_study` | Major or subject area |
| `start_year` | Year started |
| `end_year` | Year graduated |

### Experience fields
| Field | Description |
|---|---|
| `company` | Employer name |
| `title` | Job title |
| `location` | Office location |
| `start_date` | Start month in `YYYY-MM` format |
| `end_date` | End month in `YYYY-MM` format, or `null` if current |
| `is_current` | `true` if the candidate still works there |
| `description` | Role summary or bullet points |

### Certification fields
| Field | Description |
|---|---|
| `name` | Certification title |
| `issuer` | Issuing organisation |
| `year` | Year awarded |

---

## Stopping the Service

```bash
docker compose down
```

This stops and removes the containers but **preserves all data** (the database and downloaded AI model are kept in Docker volumes).

To also delete all stored data and start completely fresh:

```bash
docker compose down -v
```

---

## Troubleshooting

### "Connection refused" when calling the API

The app may still be starting up. Wait 15–20 seconds after `docker compose up -d` and try again. Check the startup logs with:

```bash
docker compose logs app
```

### Health check shows `"ollama": false`

The AI model is not yet downloaded or the Ollama service is still loading. Run:

```bash
docker compose exec ollama ollama list
```

If you see `mistral` in the list, Ollama is ready. If the list is empty, re-run the pull command from Step 3.

### `400 Bad Request` — "Unsupported file type"

Only `.pdf`, `.docx`, and `.txt` files are accepted. Ensure the file extension matches the actual file format.

### `400 Bad Request` — "Extracted text is empty"

The PDF may be a scanned image rather than a text-based PDF. The parser reads embedded text; it cannot perform OCR on scanned images. Convert the PDF to a text-searchable format first using a tool like Adobe Acrobat or an online PDF OCR service.

### `502 Bad Gateway` — Ollama not reachable

The AI server is down or overloaded. Check its status:

```bash
docker compose logs ollama
```

Restart if needed:

```bash
docker compose restart ollama
```

### Extraction looks incomplete or inaccurate

The AI model reads the resume as plain text. Results are best when:
- The resume is text-based (not a scanned image)
- Sections are clearly labelled (EXPERIENCE, EDUCATION, SKILLS, etc.)
- Dates follow a recognisable format (e.g. `2021-03`, `March 2021`, `03/2021`)

---

## Output Files

Every successful parse also writes a JSON file to the `output/` folder inside the project directory. The file is named `candidate_<short-id>.json` and contains the full structured data. These files persist on your local disk independently of the database.

---

## API Reference Summary

| Method | URL | Description |
|---|---|---|
| `GET` | `/health` | Check if all services are running |
| `POST` | `/api/v1/parse` | Upload and parse a resume |
| `POST` | `/api/v1/parse?dry_run=true` | Parse without saving to database |
| `GET` | `/api/v1/candidates/{id}` | Retrieve a previously parsed candidate |

Interactive API documentation (automatically generated) is available at:

```
http://localhost:8000/docs
```

Open that URL in a browser to explore and test all endpoints with a graphical interface — no curl required.
