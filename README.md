# EnergyGuard SonarQube Stack

Unified setup to run SonarQube with PostgreSQL and a FastAPI wrapper (`sonar-api`) that runs SonarScanner and Semgrep on uploaded code and pushes results into SonarQube.

## Components
- `sonarcube/`: SonarQube 10.5 (community) + Postgres via Docker Compose.
- `sonar-api/`: FastAPI service exposing scan endpoints, wrapping SonarScanner and optional Semgrep external issues import.

## Prerequisites
- Docker & Docker Compose
- Network `sonarqube_network` (create if missing):
  ```bash
  docker network create sonarqube_network
  ```
- A SonarQube user token with analysis rights (created after first login).

## 1) Start SonarQube
```bash
cd sonarcube
sudo docker compose up -d
```
Wait ~2–3 minutes, then open http://localhost:9000.
Default admin password is set in `sonarcube/docker-compose.yml` (`MyStrongSecurePassword!`); change it after first login.

## 2) Create a user token (UI steps)
1. Log in to SonarQube: `admin` / `MyStrongSecurePassword!` (change after first login).
2. Profile (top right) → **My Account** → **Security**.
3. Click **Generate** → Name it (e.g., `api-scanner-token`) → Type: **User Token**.
4. Generate and copy the token (you won’t see it again).

## 3) Configure the API
Edit `sonar-api/docker-compose.yml` and set your token:
```yaml
environment:
  - SONARQUBE_URL=http://sonarqube:9000
  - SONARQUBE_TOKEN=<your_token_here>
```
The compose expects the same `sonarqube_network` so the API can reach SonarQube by service name `sonarqube`.

## 4) Run the API
```bash
cd sonar-api
sudo docker compose up --build
```
Service listens on host port `9001`.

## 5) Health checks
```bash
curl http://localhost:9001/health
```
Expected:
```json
{"status":"ok","sonarqube_url":"http://sonarqube:9000","token_valid":true}
```

## 6) Scanning
### Standard Sonar scan
```bash
curl -X POST http://localhost:9001/scan \
  -F "file=@your-code.zip" \
  -F "project_name=my-project"
```

### Sonar + Semgrep external issues
```bash
curl -X POST http://localhost:9001/scan_with_semgrep \
  -F "file=@your-code.zip" \
  -F "project_name=my-project"
```
Responses include SonarQube issues/metrics and the path of the generated `semgrep_sonar.json` used as `sonar.externalIssuesReportPaths`.

## Quick path recap
- SonarQube stack: `~/energyguard-code-quality/sonarcube`
- API service: `~/energyguard-code-quality/sonar-api`
- Network expected: `sonarqube_network`

## Notes
- Workspaces are created under `/tmp/<project_key>` and cleaned after each request.
- Rebuild the API image if you change Python dependencies.
- Ensure the SonarQube token you use has rights to create/scan projects.

## Related docs
- `sonar-api/README.md` (API endpoints and usage)
- `sonarcube/README.md` (SonarQube stack details)
