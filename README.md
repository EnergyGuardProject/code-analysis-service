# EnergyGuard Code Quality

Code quality analysis platform built on Semgrep and a custom Django frontend.

## Components
- `code-analysis-backend/`: FastAPI service that runs Semgrep on uploaded code or cloned GitHub repositories and returns structured security findings.
- `code-analysis-frontend/`: Django frontend for submitting scans and viewing results.
- `sonarcube/`: Legacy SonarQube stack (no longer used by the pipeline).
- `example-python/`: Example Python projects for testing.

## Architecture

```
┌─────────────────┐
│   Browser/User  │
└────────┬────────┘
         │
         │ HTTP (port 9002)
         ▼
┌────────────────────────────────────────────────┐
│        code-analysis-frontend (Django)         │
│  • Submit code for scanning (upload or GitHub) │
│  • Display results, CWE/CVE taxonomy, hotspots │
└────────┬───────────────────────────────────────┘
         │
         │ HTTP API (port 9001)
         ▼
┌────────────────────────────────────────────────┐
│      code-analysis-backend (FastAPI)           │
│  1. Prepare workspace                          │
│  2. Run Semgrep (OSS config bundle)            │
│  3. Extract CWE/CVE taxonomy from results      │
│  4. Return structured JSON response            │
└────────────────────────────────────────────────┘

Data Flow:
1. User uploads code (file/zip) or provides a GitHub repo URL
2. Backend runs Semgrep locally on the code
3. Findings are parsed into CWE/CVE taxonomy + incident list
4. Results are returned to the frontend and persisted as JSON reports
```

## Quick start

### 1) Start the backend
```bash
cd code-analysis-backend
sudo docker compose up --build -d
```
Service listens on host port `9001`.

### 2) Health check
```bash
curl http://localhost:9001/health
```
Expected: `{"status":"ok"}`

### 3) Start the frontend
```bash
cd code-analysis-frontend
python manage.py runserver 9002
```

### 4) Scan via API
```bash
# Upload a file or ZIP
curl -X POST http://localhost:9001/scan \
  -F "file=@your-code.zip" \
  -F "project_name=my-project"

# Scan a GitHub repository
curl -X POST http://localhost:9001/scan_github \
  -F "repo_url=https://github.com/org/repo.git" \
  -F "project_name=my-project" \
  -F "branch=main"
```

## Notes
- Workspaces are created under `/tmp/<project_key>` and cleaned after each request.
- Rebuild the backend image if you change Python dependencies.
- Frontend env var: `SCAN_API_URL` (default: `http://127.0.0.1:9001`).

## Related docs
- `code-analysis-backend/README.md` (API endpoints and usage)
