# Django Frontend Prototype

This folder contains a Django frontend prototype for the code analysis tool mockups.

## Structure

- `code_analysis_frontend/`: Django project config
- `analysis_ui/`: UI app with templates and static assets
- `analysis_ui/templates/analysis_ui/mockup1.html`: Implemented first screen
- `analysis_ui/static/analysis_ui/css/mockup1.css`: Styling for mockup 1

## Run locally

```bash
cd /home/atzortzis/energyguard-code-quality/code-analysis-frontend
```

Open: `http://127.0.0.1:9002/`

## Run with Docker Compose

From `code-analysis-frontend/`:

```bash
docker compose up --build
```

Open: `http://127.0.0.1:9002/`

Stop containers:

```bash
docker compose down
```

If your backend API is running on your host at port `9001`, set:

```bash
SCAN_API_URL=http://host.docker.internal:9001 docker compose up --build
```

On Linux, if `host.docker.internal` does not resolve, use your host IP instead.

## Run without Docker

Use the existing virtual environment from the repo root:

```bash
cd /home/atzortzis/energyguard-code-quality/code-analysis-frontend
/home/atzortzis/energyguard-code-quality/code-analysis-venv/bin/pip install -r requirements.txt
/home/atzortzis/energyguard-code-quality/code-analysis-venv/bin/python manage.py migrate
/home/atzortzis/energyguard-code-quality/code-analysis-venv/bin/python manage.py runserver 9002
```

## Delivery plan

1. `mockup1` - Select Source screen (implemented)
2. `mockup2` - Configure Upload ZIP screen
3. `mockup3` - Configure GitHub Repository screen
4. `mockup4` - Configure JupyterHub Workspace screen
5. `mockup5` - Results dashboard screen
