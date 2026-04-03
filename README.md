# Resume Parser — User Guide

This guide walks you through setting up and using the Resume Parser. You can upload a resume through a browser UI and instantly see the structured data extracted from it — no manual data entry, no cloud APIs, all processing on your machine.

---

## What Does This Tool Do?

You upload a resume (PDF, Word document, or plain text file) through the browser. The tool reads it, sends the text to a local AI model running on your machine, and displays structured data like this:

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

Results are shown in both a formatted table view and raw JSON. Every successful parse is saved as a JSON file in the `output/` folder. The **All Candidates** page lets you browse every previously parsed resume.

All processing happens **on your machine**. No data is sent to any external service or cloud API. Parsed data is stored as JSON files on disk — no database is used.

---

## What You Need Before Starting

| Requirement | Why | Install |
|---|---|---|
| **Python 3.11+** | Runs the backend API | https://www.python.org/downloads/ |
| **Node.js 18+** | Runs the React frontend | `brew install node` |
| **Ollama** | Runs the local AI model | `brew install ollama` |
| **8 GB RAM** | Recommended for comfortable AI model inference | — |
| **4 GB free disk space** | Stores the AI model (~4 GB for Mistral) | — |

---

## Step 1 — Download the Project

```bash
git clone <repository-url>
cd resume-parser-workflow
```

---

## Step 2 — Install the AI Model (First Time Only)

```bash
# Start the Ollama server
ollama serve

# In a separate terminal, pull the model (~4 GB download)
ollama pull mistral
```

The model is saved locally and only needs to be downloaded once.

---

## Step 3 — Install Dependencies

```bash
# Python dependencies
pip install -e ".[dev]"

# Node dependencies (backend dev runner + frontend)
npm install
cd frontend && npm install && cd ..
```

---

## Step 4 — Configure Environment

```bash
cp .env.example .env
```

The defaults work for local development. The key settings are:

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
OUTPUT_DIR=./output
```

No API keys are required.

---

## Step 5 — Start the Application

```bash
npm run dev
```

This starts both servers simultaneously:
- **Backend API**: `http://localhost:8000`
- **Frontend UI**: `http://localhost:3000`

Open `http://localhost:3000` in your browser.

---

## Using the UI

### Upload a Resume

1. Navigate to the **Upload Resume** tab.
2. Drag and drop a file onto the upload area, or click to select one.
3. Supported formats: `.pdf`, `.docx`, `.txt`
4. Wait for the AI to process the resume (this can take 5–30 seconds depending on your hardware).
5. The extracted data appears in two tabs:
   - **Structured** — formatted table with all fields, skill tags, education cards, and experience cards.
   - **Raw JSON** — the complete JSON output.

### Browse All Candidates

1. Click **All Candidates** in the navigation bar.
2. The table shows all previously parsed resumes, sorted newest first.
3. Click any row to expand an inline detail panel for that candidate.
4. Use **Prev** / **Next** to page through results.

---

## How Parsed Data Is Stored

Every successful parse writes a JSON file to the `output/` directory:

```
output/
├── candidate_a3f8c2e1.json
├── candidate_b7d4f912.json
└── ...
```

The **All Candidates** page reads directly from these files — no database is involved. The `id` shown in the UI is the filename stem (e.g. `candidate_a3f8c2e1`).

---

## API Reference

The backend exposes a REST API. Interactive documentation is at `http://localhost:8000/docs`.

| Method | URL | Description |
|---|---|---|
| `GET` | `/health` | Check if backend and Ollama are running |
| `POST` | `/api/v1/parse?dry_run=true` | Upload and parse a resume; returns structured data; no DB write |
| `GET` | `/api/v1/candidates` | List all parsed candidates from `output/` (paginated) |
| `GET` | `/api/v1/candidates/{id}` | Fetch a single candidate by filename stem |

### List candidates query parameters

| Parameter | Default | Description |
|---|---|---|
| `limit` | 20 | Number of results per page (max 100) |
| `offset` | 0 | Number of records to skip |

### Example: parse via curl

```bash
curl -X POST "http://localhost:8000/api/v1/parse?dry_run=true" \
  -F "file=@/path/to/resume.pdf"
```

### Example: list candidates via curl

```bash
curl "http://localhost:8000/api/v1/candidates?limit=10&offset=0"
```

### Example: fetch a specific candidate

```bash
curl "http://localhost:8000/api/v1/candidates/candidate_a3f8c2e1"
```

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
| `summary` | Professional summary | `"8 years of experience..."` |
| `skills` | Technical and soft skills | `["Python", "Docker"]` |
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

## Troubleshooting

### `502 Bad Gateway` — Ollama not reachable

Ensure Ollama is running:

```bash
ollama serve
```

### `422` — Extraction or validation error

The AI may have returned incomplete data. Try again — results can vary between runs. If it consistently fails, try a different model:

```bash
ollama pull llama3
# then set OLLAMA_MODEL=llama3 in .env
```

### `400 Bad Request` — Unsupported file type

Only `.pdf`, `.docx`, and `.txt` files are accepted.

### `400 Bad Request` — Extracted text is empty

The PDF may be a scanned image rather than text-based. The parser reads embedded text; it cannot perform OCR. Convert the PDF to a text-searchable format first.

### Frontend shows no candidates

Check that the `output/` directory exists and contains `*.json` files. Each file corresponds to one parsed resume.

### Port already in use

If port 8000 or 3000 is taken, stop the conflicting process or update the port in `vite.config.js` (frontend) and the `npm run dev` script in the root `package.json`.

---

## CLI Usage (Advanced)

The original CLI interface is still available for scripted or batch processing:

```bash
# Full pipeline (writes JSON + inserts to DB if DATABASE_URL is configured)
python -m src.main process --file ./sample_resume.pdf

# Dry run (writes JSON only, skips DB insert)
python -m src.main process --file ./sample_resume.pdf --dry-run
```
