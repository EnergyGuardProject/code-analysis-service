# Code Analysis Backend

FastAPI service that runs Semgrep on uploaded code or cloned GitHub repositories and returns structured security findings (CWE/CVE taxonomy, incidents, statistics).

## Prerequisites
- Docker & Docker Compose

## Build and run
From this folder:
```bash
sudo docker compose up --build
```
Service listens on port `9001` (mapped to container `5000`).

## Key endpoints
- `GET /health` — service health check
- `POST /scan` — upload a file or ZIP (`file`, `project_name`); runs Semgrep
- `POST /scan_with_semgrep` — alias of `/scan`
- `POST /scan_github` — clone a GitHub repo (`repo_url`, `project_name`, optional `branch`, `subdirectory`, `access_token`) and run Semgrep
- `POST /scan_github_with_semgrep` — alias of `/scan_github`

### Scanning example (file upload)
```bash
curl -X POST http://localhost:9001/scan \
  -F "file=@path/to/myfile.py" \
  -F "project_name=myproject"
```

### Scanning example (ZIP upload)
```bash
curl -X POST http://localhost:9001/scan \
  -F "file=@src.zip" \
  -F "project_name=myproject"
```

### Scanning example (GitHub repo)
```bash
curl -X POST http://localhost:9001/scan_github \
  -F "repo_url=https://github.com/org/repository.git" \
  -F "project_name=myproject" \
  -F "branch=main"
```

## Semgrep config bundle
Findings are collected using these OSS rulesets:
- `p/bandit`
- `p/findsecbugs`
- `p/flawfinder`
- `p/phpcs-security-audit`
- `p/security-code-scan`
- `p/eslint`
- `p/gitleaks`

## Response format
All scan endpoints return a JSON object with a `taxonomy` key containing:
- `cwe` / `cve` — sorted lists of detected identifiers
- `incidents` — per-finding details (rule, message, location, severity, CWE refs)
- `standards` — deduplicated standard rows for display
- `by_rule` — metadata grouped by Semgrep rule ID
- `stats` — `files_scanned`, `findings_total`, `scan_time_sec`
- `scanned_files` — normalized list of scanned file paths

## Notes
- Workspaces are created under `/tmp/<project_key>` and cleaned after each request.
- If you change dependencies, rebuild the image.
