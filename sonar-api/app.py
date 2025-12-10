import os
import shutil
import zipfile
import subprocess
import time
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from requests.auth import HTTPBasicAuth
import json
from pathlib import Path

# ------------------------------
# CONFIG
# ------------------------------
SONAR_URL = os.getenv("SONARQUBE_URL", "http://energyguard.epu.ntua.gr:9000")
SONAR_TOKEN = os.getenv("SONARQUBE_TOKEN")
SONAR_SCANNER = os.getenv("SONAR_SCANNER_PATH", "sonar-scanner")

if not SONAR_TOKEN:
    raise Exception("Missing SONARQUBE_TOKEN environment variable")

auth = HTTPBasicAuth(SONAR_TOKEN, "")

app = FastAPI(title="SonarQube API Wrapper")

# ------------------------------
# HELPERS
# ------------------------------

def semgrep_to_sonar_json(semgrep_json_path: str, output_path: str):
    """
    Convert Semgrep JSON output to SonarQube Generic Issue JSON format.
    
    semgrep_json_path: Path to semgrep JSON output
    output_path: Path to save SonarQube-compatible JSON
    """
    if not os.path.exists(semgrep_json_path):
        # If no semgrep output, create empty issues file
        with open(output_path, "w") as f:
            json.dump({"issues": []}, f, indent=2)
        return
    
    with open(semgrep_json_path, "r") as f:
        semgrep_data = json.load(f)

    sonar_issues = []
    for issue in semgrep_data.get("results", []):
        start_line = issue.get("start", {}).get("line", 0)
        end_line = issue.get("end", {}).get("line", start_line)
        severity_map = {
            "ERROR": "CRITICAL",
            "WARNING": "MAJOR",
            "INFO": "MINOR"
        }
        sonar_issues.append({
            "engineId": "semgrep",
            "ruleId": issue.get("check_id", "semgrep"),
            "primaryLocation": {
                "filePath": issue.get("path"),
                "message": issue.get("extra", {}).get("message", issue.get("message", "")),
                "textRange": {"startLine": start_line, "endLine": end_line}
            },
            "type": "CODE_SMELL",
            "severity": severity_map.get(issue.get("extra", {}).get("severity", "INFO").upper(), "MAJOR")
        })

    # SonarQube expects the root to be an object with an 'issues' key
    with open(output_path, "w") as f:
        json.dump({"issues": sonar_issues}, f, indent=2)

def prepare_workspace(upload: UploadFile, project_key: str) -> str:
    """
    Prepare a temporary workspace for scanning an uploaded file.

    - Single file → moved into a src/ folder
    - ZIP archive → extracted into workspace
    - Returns path to workspace directory
    """
    workspace = f"/tmp/{project_key}"

    # Clean up any existing workspace
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace, exist_ok=True)

    # Path to the uploaded file
    file_path = os.path.join(workspace, upload.filename)
    with open(file_path, "wb") as f:
        f.write(upload.file.read())

    # Handle ZIP archive
    if upload.filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(workspace)
        os.remove(file_path)
    else:
        # Single file → move to src/ subfolder
        src_dir = os.path.join(workspace, "src")
        os.makedirs(src_dir, exist_ok=True)
        shutil.move(file_path, os.path.join(src_dir, upload.filename))

    return workspace

def run_sonar_scanner(project_key: str, src_path: str):
    cmd = [
        SONAR_SCANNER,
        f"-Dsonar.projectKey={project_key}",
        f"-Dsonar.sources={src_path}",
        f"-Dsonar.host.url={SONAR_URL}",
        f"-Dsonar.login={SONAR_TOKEN}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"SonarScanner failed:\n{result.stderr}")
    return result.stdout

def sonar_get(endpoint: str, params: dict = None):
    url = f"{SONAR_URL}{endpoint}"
    resp = requests.get(url, auth=auth, params=params)
    resp.raise_for_status()
    return resp.json()

def sonar_post(endpoint: str, params: dict = None):
    url = f"{SONAR_URL}{endpoint}"
    resp = requests.post(url, auth=auth, params=params)
    resp.raise_for_status()
    return resp.json()

# ------------------------------
# ENDPOINTS
# ------------------------------

@app.get("/health", tags=["Health"])
def health():
    """Check API health and SonarQube connection."""
    return {"status": "ok", "sonarqube_url": SONAR_URL, "token_valid": True}

@app.get("/validate_token", tags=["Authentication"])
def validate_token():
    """Validate SonarQube authentication token."""
    try:
        data = sonar_get("/api/authentication/validate")
        return data
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/projects", tags=["Projects"])
def list_projects(q: str = None, page_size: int = 100):
    """List all SonarQube projects with optional search filter."""
    try:
        return sonar_get("/api/projects/search", params={"q": q, "ps": page_size})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/projects", tags=["Projects"])
def create_project(project_name: str = Form(...), project_key: str = Form(None)):
    """Create a new SonarQube project."""
    key = project_key or project_name.lower().replace(" ", "_").replace("-", "_")
    try:
        sonar_post("/api/projects/create", params={"project": key, "name": project_name})
        return {"project_key": key, "project_name": project_name, "status": "created_or_existing"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/projects/{project_key}", tags=["Projects"])
def delete_project(project_key: str):
    """Delete a SonarQube project."""
    try:
        # POST request to delete project
        return sonar_post("/api/projects/delete", params={"project": project_key})
    except requests.HTTPError as e:
        # SonarQube returns 403 if you don't have permissions
        return JSONResponse({"error": str(e), "status_code": e.response.status_code}, status_code=500)

@app.post("/scan_with_semgrep", tags=["Scanning"])
async def scan_with_semgrep(file: UploadFile = File(...), project_name: str = Form(...)):
    """
    Scan a project file with SonarQube AND Semgrep, 
    pushing Semgrep results as external issues.
    """
    project_key = project_name.lower().replace(" ", "_").replace("-", "_")
    workspace = None
    sonar_ext_json = None
    try:
        workspace = prepare_workspace(file, project_key)

        # Create project if it doesn't exist
        try:
            sonar_post("/api/projects/create", params={"project": project_key, "name": project_name})
        except requests.HTTPError as e:
            if e.response.status_code != 400:  # Ignore "already exists"
                raise

        # --- Run Semgrep ---
        semgrep_json = os.path.join(workspace, "semgrep.json")
        result = subprocess.run(
            ["semgrep", "--config", "r/all", "--json", "--timeout", "60", workspace, "-o", semgrep_json],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Semgrep warning: {result.stderr}")

        # Convert to SonarQube generic issues (save to workspace root)
        sonar_ext_json = os.path.join(workspace, "semgrep_sonar.json")
        semgrep_to_sonar_json(semgrep_json, sonar_ext_json)

        # Verify the file was created and has content
        if not os.path.exists(sonar_ext_json):
            raise Exception(f"External issues file was not created: {sonar_ext_json}")
        
        file_size = os.path.getsize(sonar_ext_json)
        if file_size == 0:
            raise Exception(f"External issues file is empty: {sonar_ext_json}")
        
        # Read and verify JSON is valid
        with open(sonar_ext_json, "r") as f:
            json_content = json.load(f)
            issue_count = len(json_content.get('issues', []))
            print(f"External issues file created with {issue_count} issues")

        # --- Run SonarScanner with external issues ---
        # Use relative path from workspace for the external issues report
        cmd = [
            SONAR_SCANNER,
            f"-Dsonar.projectKey={project_key}",
            f"-Dsonar.sources={workspace}",
            f"-Dsonar.host.url={SONAR_URL}",
            f"-Dsonar.login={SONAR_TOKEN}",
            f"-Dsonar.externalIssuesReportPaths=semgrep_sonar.json"
        ]
        
        # Run scanner from the workspace directory so relative path works
        scan_result = subprocess.run(cmd, capture_output=True, text=True, cwd=workspace)
        print(f"SonarScanner stdout: {scan_result.stdout}")
        print(f"SonarScanner stderr: {scan_result.stderr}")
        
        if scan_result.returncode != 0:
            raise Exception(f"SonarScanner failed:\n{scan_result.stderr}")

        # Wait for analysis to complete
        time.sleep(5)

        # Fetch issues and metrics
        issues = sonar_get("/api/issues/search", params={"projectKeys": project_key})
        metrics = sonar_get("/api/measures/component", params={
            "component": project_key,
            "metricKeys": "bugs,vulnerabilities,code_smells,coverage"
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        if workspace and os.path.exists(workspace):
            shutil.rmtree(workspace, ignore_errors=True)

    return {
        "project_key": project_key,
        "project_name": project_name,
        "scan_output": scan_result.stdout[:500] if scan_result else "No output",
        "issues": issues,
        "metrics": metrics,
        "issues_found": len(issues.get("issues", []))
    }

@app.post("/scan", tags=["Scanning"])
async def scan(file: UploadFile = File(...), project_name: str = Form(...)):
    """Scan a project file and analyze it with SonarQube."""
    project_key = project_name.lower().replace(" ", "_").replace("-", "_")
    try:
        workspace = prepare_workspace(file, project_key)
        # Try to create project, but don't fail if it already exists
        try:
            sonar_post("/api/projects/create", params={"project": project_key, "name": project_name})
        except requests.HTTPError as e:
            # 400 Bad Request likely means project already exists, continue
            if e.response.status_code != 400:
                raise
        output = run_sonar_scanner(project_key, workspace)
        time.sleep(3)
        issues = sonar_get("/api/issues/search", params={"projectKeys": project_key})
        metrics = sonar_get("/api/measures/component", params={
            "component": project_key,
            "metricKeys": "bugs,vulnerabilities,code_smells,coverage"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    return {"project_key": project_key, "project_name": project_name, "scan_output": output[:500], "issues": issues, "metrics": metrics}

@app.get("/projects/{project_key}/quality_gate", tags=["Projects"])
def quality_gate(project_key: str):
    """Get quality gate status for a project."""
    try:
        return sonar_get("/api/qualitygates/project_status", params={"projectKey": project_key})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/projects/{project_key}/branches", tags=["Branches"])
def list_branches(project_key: str):
    """List all branches of a project."""
    try:
        return sonar_get("/api/project_branches/list", params={"project": project_key})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/projects/{project_key}/pull_requests", tags=["Pull Requests"])
def list_pull_requests(project_key: str):
    """List all pull requests of a project."""
    try:
        return sonar_get("/api/project_pull_requests/list", params={"project": project_key})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/projects/{project_key}/issues", tags=["Issues"])
def project_issues(project_key: str, severities: str = None, statuses: str = None):
    """Get issues for a project with optional filtering."""
    params = {"projectKeys": project_key}
    if severities:
        params["severities"] = severities
    if statuses:
        params["statuses"] = statuses
    try:
        return sonar_get("/api/issues/search", params=params)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/projects/{project_key}/metrics", tags=["Metrics"])
def project_metrics(project_key: str):
    """Get metrics for a project (bugs, vulnerabilities, code smells, coverage, duplicates)."""
    try:
        return sonar_get("/api/measures/component", params={
            "component": project_key,
            "metricKeys": "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/rules", tags=["Rules"])
def list_rules(language: str = None, tag: str = None):
    """List SonarQube rules with optional language or tag filter."""
    params = {}
    if language:
        params["languages"] = language
    if tag:
        params["tags"] = tag
    try:
        return sonar_get("/api/rules/search", params=params)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/rules/{rule_key}", tags=["Rules"])
def rule_details(rule_key: str):
    """Get details of a specific SonarQube rule."""
    try:
        return sonar_get("/api/rules/show", params={"key": rule_key})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
