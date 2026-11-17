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
│  2. Run Semgrep (vendored open-source rules)   │
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

There are two Docker recipes at the repository root. They use different projects, containers, networks, ports and
images, so both can run at the same time.

| | Production: `docker-compose.yml` | Development: `docker-compose.dev.yml` |
|---|---|---|
| Containers | `code_analysis_backend`, `code-analysis-frontend` | `code_analysis_backend_dev`, `code_analysis_frontend_dev` |
| Ports | backend `9001`, frontend `9002` | backend `9011`, frontend `9012` |
| Images | `energyguard-code-quality-code-analysis-backend:prod` and `...-frontend:prod` | the same names with the tag `:dev` |
| Code | baked into the image (backend) | mounted: edits to `app.py` and `rules/` apply without a rebuild |
| Used by | the EnergyGuard dashboard (`http://code_analysis_backend:5000`) | you |

A `Makefile` wraps the common commands, with a comment on each: run `make help` for the list (`make dev-up`,
`make test-rules`, `make prod-status`, `make prod-test-dev`, `make prod-promote`, `make prod-rollback TAG=...`).
Targets that change the live service ask for confirmation first. It needs `make` (`sudo apt install make`).

### Development
```bash
docker compose -f docker-compose.dev.yml up --build      # backend :9011, frontend :9012
curl http://localhost:9011/health                         # {"status":"ok"}
docker compose -f docker-compose.dev.yml down
```
The frontend runs as root inside its container and writes reports to `code-analysis-frontend/analysis_reports/`; to
delete those files use `docker exec code_analysis_frontend_dev rm -rf /app/analysis_reports/<job id>`.

### Production and releases
Both stacks use the same image names; the **tag** tells them apart: `:prod` is what runs live (and the default of
`docker-compose.yml`), `:dev` is built from the working tree by the development stack, and `:prod-YYYY-MM-DD` are dated
copies of earlier `:prod` images for rolling back. Below, `IMG` is `energyguard-code-quality-code-analysis-backend`.

```bash
# 1. build the candidate (the dev stack builds :dev from the working tree)
docker compose -f docker-compose.dev.yml build

# 2. try it with the dashboard (the container keeps its name, network and port; a few seconds of downtime)
TAG=dev docker compose up -d --no-build code-analysis-backend

# 3a. roll back to a dated copy
TAG=prod-2026-11-05 docker compose up -d --no-build code-analysis-backend

# 3b. or keep it: save the old :prod, promote :dev to :prod, restart on it
docker tag IMG:prod IMG:prod-$(date +%F) && docker tag IMG:dev IMG:prod
docker compose up -d --no-build code-analysis-backend
```
Keep the container name `code_analysis_backend`, the network and the project name (the directory name): the dashboard
finds the backend by that name. A tag is only a label: an image stays on disk while any tag points to it, so avoid
`docker image prune` while you still need a rollback copy that has no tag.

### Scan via API
Use port `9011` (development) or `9001` (production).
```bash
# Upload a file or ZIP
curl -X POST http://localhost:9011/scan \
  -F "file=@your-code.zip" \
  -F "project_name=my-project"

# Scan a GitHub repository
curl -X POST http://localhost:9011/scan_github \
  -F "repo_url=https://github.com/org/repo.git" \
  -F "project_name=my-project" \
  -F "branch=main"
```

## Notes
- Workspaces are created under `/tmp/<project_key>` and cleaned after each request.
- Rebuild the backend image if you change Python dependencies.
- Frontend env var: `SCAN_API_URL` (default: `http://127.0.0.1:9001`).

## License
This project is licensed under the [GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0-or-later): the source is open, you can use, modify and sell services built on it, and anyone who runs a modified version as a network service must offer its source to the users of that service.

The Semgrep rules in `code-analysis-backend/rules/` come from other projects under their own open-source licences (MIT, Apache-2.0, GPL-2.0-or-later, LGPL-3.0), listed with their obligations in [`code-analysis-backend/rules/NOTICE.md`](code-analysis-backend/rules/NOTICE.md).

## Related docs
- `code-analysis-backend/README.md` (API endpoints and usage)
