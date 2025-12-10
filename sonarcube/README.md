# SonarQube Stack

Docker Compose stack for SonarQube (10.5 community) with PostgreSQL.

## Prerequisites
- Docker & Docker Compose
- External Docker network named `sonarqube_network` (create if missing):
  ```bash
  docker network create sonarqube_network
  ```

## Run
From this folder:
```bash
sudo docker compose up -d
```
Then wait ~2–3 minutes and visit http://localhost:9000.

## Default credentials
- User: `admin`
- Password: `MyStrongSecurePassword!` (set via compose env; change after first login)

## Volumes
- `sonarqube_data` → SonarQube data
- `sonarqube_extensions` → Plugins
- `sonarqube_db_data` → Postgres data

## Generate a token
1. Login as admin
2. Profile → **My Account** → **Security**
3. Generate a token (User Analysis Token) and copy it

Use this token in the API service (see `../sonar-api/docker-compose.yml`).

## Stop / remove
```bash
sudo docker compose down
```
(Volumes are preserved; add `-v` to remove persisted data.)
