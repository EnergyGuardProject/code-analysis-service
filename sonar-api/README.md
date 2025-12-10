# Sonar API Wrapper

FastAPI service that wraps SonarScanner and Semgrep to scan uploaded projects and push findings to SonarQube as analyses and external issues.

## Prerequisites
- Docker & Docker Compose
- Running SonarQube instance reachable at `SONARQUBE_URL`
- SonarQube user token with scan rights (`SONARQUBE_TOKEN`)
- Docker network shared with SonarQube (default: `sonarqube_network`)

## Configuration
Update `docker-compose.yml` (or use env vars) before `up`:
- `SONARQUBE_URL` (e.g., `http://sonarqube:9000`)
- `SONARQUBE_TOKEN` (replace any placeholder token)

If the shared network does not exist:
```bash
docker network create sonarqube_network
```

## Build and run
From this folder:
```bash
sudo docker compose up --build
```
Service listens on port `9001` (mapped to container `5000`).

## Key endpoints
- `GET /health` — service/connection check
- `GET /validate_token` — verifies the token against SonarQube
- `GET /projects` — list projects (optional `q` filter)
- `POST /projects` — create a project (`project_name`, optional `project_key`)
- `DELETE /projects/{project_key}` — delete a project
- `POST /scan` — upload a file/zip (`file`) and `project_name`; runs SonarScanner
- `POST /scan_with_semgrep` — like `/scan`, but also runs Semgrep and imports findings as external issues

### Scanning example (single file)
```bash
curl -X POST http://localhost:9001/scan \
  -F "file=@path/to/myfile.py" \
  -F "project_name=myproject"
```

### Scanning example (zip + Semgrep external issues)
```bash
curl -X POST http://localhost:9001/scan_with_semgrep \
  -F "file=@src.zip" \
  -F "project_name=myproject"
```

## How Semgrep issues are imported
- Semgrep runs with `--config r/all` and outputs JSON.
- The service converts results to SonarQube Generic Issues format (`semgrep_sonar.json`).
- SonarScanner is invoked with `-Dsonar.externalIssuesReportPaths=semgrep_sonar.json`.

## Notes
- Workspaces are created under `/tmp/<project_key>` and cleaned after each request.
- If you change dependencies, rebuild the image.
- Tokens in the compose file are placeholders; replace with your own before running.
