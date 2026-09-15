import os
import shutil
import zipfile
import subprocess
import json
import re
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

# ------------------------------
# CONFIG
# ------------------------------
SEMGREP_OSS_CONFIGS = [
    "p/bandit",
    "p/findsecbugs",
    "p/flawfinder",
    "p/phpcs-security-audit",
    "p/security-code-scan",
    "p/eslint",
    "p/gitleaks",
]

app = FastAPI(title="Code Analysis Backend")

NOTEBOOK_CHECKPOINTS_DIR = ".ipynb_checkpoints"

# ------------------------------
# HELPERS
# ------------------------------

def build_semgrep_command(source_path: str, output_path: str):
    cmd = ["semgrep"]
    for config in SEMGREP_OSS_CONFIGS:
        cmd.extend(["--config", config])
    cmd.extend(["--json", "--timeout", "60", source_path, "-o", output_path])
    return cmd


def _normalize_issue_location(issue_path: str, source_root: str | None = None) -> str:
    """Return a run-local, readable file path for UI cards."""
    raw = str(issue_path or "").strip()
    if not raw:
        return "unknown"

    candidate = Path(raw)
    if source_root:
        try:
            root = Path(source_root).resolve()
            resolved_candidate = candidate.resolve()
            if resolved_candidate == root or root in resolved_candidate.parents:
                return str(resolved_candidate.relative_to(root)) or "."
        except (OSError, RuntimeError, ValueError):
            pass

    parts = [p for p in candidate.parts if p and p not in ("/", "\\")]
    if len(parts) >= 3:
        return "/".join(parts[-3:])
    if parts:
        return "/".join(parts)
    return raw


def extract_semgrep_taxonomy(
    semgrep_json_path: str,
    source_root: str | None = None,
    notebook_maps: dict[str, list[tuple[int, int]]] | None = None,
) -> dict:
    """Extract CWE/CVE references directly from raw Semgrep JSON metadata."""
    if not os.path.exists(semgrep_json_path):
        return {
            "cwe": [],
            "cve": [],
            "standards": [],
            "by_rule": {},
            "incidents": [],
            "stats": {"files_scanned": 0, "findings_total": 0, "scan_time_sec": 0.0},
        }

    with open(semgrep_json_path, "r") as f:
        semgrep_data = json.load(f)

    notebook_maps = notebook_maps or {}
    cwe_ids = set()
    cve_ids = set()
    standard_rows = []
    seen_rows = set()
    rule_index = {}
    incidents = []
    results = semgrep_data.get("results", [])
    scanned_files = semgrep_data.get("paths", {}).get("scanned", [])
    normalized_scanned_files = [
        _resolve_notebook_location(_normalize_issue_location(path, source_root), None, notebook_maps)[0]
        for path in scanned_files
        if str(path or "").strip()
    ]
    scan_time_sec = float(semgrep_data.get("time", {}).get("profiling_times", {}).get("total_time", 0.0) or 0.0)

    for issue in results:
        extra = issue.get("extra", {})
        metadata = extra.get("metadata", {})
        search_blobs = [
            issue.get("check_id", ""),
            extra.get("message", ""),
            metadata.get("shortDescription", ""),
            metadata.get("source", ""),
        ]

        short_desc = str(metadata.get("shortDescription") or "").strip()
        message = str(extra.get("message") or "").strip()
        title = short_desc or message or str(issue.get("check_id") or "Semgrep finding")
        description = message if message and message != title else ""
        severity_raw = str(metadata.get("security-severity") or extra.get("severity") or "INFO").upper()
        if severity_raw in {"CRITICAL", "HIGH", "ERROR"}:
            severity = "HIGH"
            issue_severity = "ERROR"
        elif severity_raw in {"MEDIUM", "WARNING", "WARN", "MAJOR"}:
            severity = "MEDIUM"
            issue_severity = "WARNING"
        elif severity_raw in {"LOW", "MINOR", "INFO"}:
            severity = "LOW"
            issue_severity = "INFO"
        else:
            severity = "INFO"
            issue_severity = "INFO"

        cwe_meta = metadata.get("cwe")
        if isinstance(cwe_meta, str):
            search_blobs.append(cwe_meta)
        elif isinstance(cwe_meta, list):
            search_blobs.extend([str(item) for item in cwe_meta])

        refs = metadata.get("references")
        if isinstance(refs, list):
            search_blobs.extend([str(item) for item in refs])

        blob = " ".join(search_blobs)

        rule_id = str(issue.get("check_id") or "").strip()
        rule_cwe = set()
        rule_cve = set()
        cwe_descriptions = set()

        for match in re.findall(r"CWE[-:_ ]?(\d+)", blob, flags=re.IGNORECASE):
            standard = f"CWE-{match}"
            cwe_ids.add(standard)
            rule_cwe.add(standard)
            row_key = (standard, title)
            if row_key not in seen_rows:
                seen_rows.add(row_key)
                standard_rows.append(
                    {
                        "standard": standard,
                        "title": title,
                        "description": description,
                        "severity": severity,
                    }
                )

        cwe_items = []
        if isinstance(cwe_meta, str):
            cwe_items = [cwe_meta]
        elif isinstance(cwe_meta, list):
            cwe_items = [str(item) for item in cwe_meta]
        for item in cwe_items:
            match = re.search(r"(CWE[-:_ ]?\d+)\s*[:\-]\s*(.+)", item, flags=re.IGNORECASE)
            if match:
                cwe_id = re.sub(r"[-:_ ]+", "-", match.group(1).upper()).replace("CWE-", "CWE-")
                cwe_id = re.sub(r"CWE-(\d+).*", r"CWE-\1", cwe_id)
                cwe_desc = match.group(2).strip()
                if cwe_desc:
                    cwe_descriptions.add(f"{cwe_id}: {cwe_desc}")

        for match in re.findall(r"CVE-\d{4}-\d+", blob, flags=re.IGNORECASE):
            standard = match.upper()
            cve_ids.add(standard)
            rule_cve.add(standard)
            row_key = (standard, title)
            if row_key not in seen_rows:
                seen_rows.add(row_key)
                standard_rows.append(
                    {
                        "standard": standard,
                        "title": title,
                        "description": description,
                        "severity": severity,
                    }
                )

        if rule_id:
            bucket = rule_index.setdefault(rule_id, {"cwe": set(), "cve": set(), "meta": {}})
            bucket["cwe"].update(rule_cwe)
            bucket["cve"].update(rule_cve)

            metadata_fields = {
                "category": metadata.get("category"),
                "security_severity": metadata.get("security-severity"),
                "short_description": metadata.get("shortDescription"),
                "cwe": ", ".join(sorted(rule_cwe)) if rule_cwe else None,
                "cwe_description": "; ".join(sorted(cwe_descriptions)) if cwe_descriptions else None,
                "owasp": metadata.get("owasp"),
                "vulnerability_class": metadata.get("vulnerability_class"),
                "likelihood": metadata.get("likelihood"),
                "impact": metadata.get("impact"),
                "confidence": metadata.get("confidence"),
                "source": metadata.get("source"),
                "references": metadata.get("references"),
                "primary_identifier": metadata.get("primary_identifier"),
                "technology": metadata.get("technology"),
            }
            for key, value in metadata_fields.items():
                if value in (None, "", [], {}):
                    continue
                if isinstance(value, list):
                    value = ", ".join(str(item) for item in value if item not in (None, ""))
                bucket["meta"][key] = str(value)

        metadata_rows = []
        if rule_id and rule_id in rule_index:
            for key, value in rule_index[rule_id].get("meta", {}).items():
                label = key.replace("_", " ").title()
                metadata_rows.append({"key": label, "value": value})
        metadata_rows.sort(key=lambda item: item["key"])

        location, line = _resolve_notebook_location(
            _normalize_issue_location(issue.get("path") or "unknown", source_root),
            issue.get("start", {}).get("line"),
            notebook_maps,
        )

        incidents.append(
            {
                "rule": rule_id or "semgrep",
                "message": message or title,
                "location": location,
                "line": line,
                "severity": issue_severity,
                "status": "OPEN",
                "effort": "n/a",
                "type": metadata.get("category", "security").upper(),
                "cwe_refs": sorted(rule_cwe),
                "cve_refs": sorted(rule_cve),
                "metadata_rows": metadata_rows,
            }
        )

    return {
        "cwe": sorted(cwe_ids),
        "cve": sorted(cve_ids),
        "scanned_files": sorted(set(normalized_scanned_files)),
        "standards": standard_rows,
        "by_rule": {
            key: {
                "cwe": sorted(value["cwe"]),
                "cve": sorted(value["cve"]),
                "meta": value.get("meta", {}),
            }
            for key, value in rule_index.items()
        },
        "incidents": incidents,
        "stats": {
            "files_scanned": len(scanned_files),
            "findings_total": len(results),
            "scan_time_sec": scan_time_sec,
        },
    }


def prepare_workspace(upload: UploadFile, project_key: str) -> str:
    """Prepare a temporary workspace for scanning an uploaded file."""
    workspace = f"/tmp/{project_key}"

    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace, exist_ok=True)

    file_path = os.path.join(workspace, upload.filename)
    with open(file_path, "wb") as f:
        f.write(upload.file.read())

    if upload.filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(workspace)
        os.remove(file_path)
    else:
        src_dir = os.path.join(workspace, "src")
        os.makedirs(src_dir, exist_ok=True)
        shutil.move(file_path, os.path.join(src_dir, upload.filename))

    return workspace


def normalize_project_key(project_name: str) -> str:
    return project_name.lower().replace(" ", "_").replace("-", "_")


def build_clone_url(repo_url: str, access_token: str | None = None) -> str:
    repo_url = repo_url.strip()
    parsed = urlsplit(repo_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise Exception("Repository URL must be a valid HTTP(S) URL.")

    if not access_token:
        return repo_url

    token = quote(access_token, safe="")
    netloc = f"x-access-token:{token}@{parsed.netloc}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def prepare_repo_workspace(repo_url: str, project_key: str, branch: str | None = None, access_token: str | None = None) -> str:
    workspace = f"/tmp/{project_key}"

    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    clone_cmd = ["git", "clone", "--depth", "1"]
    if branch:
        clone_cmd.extend(["--branch", branch])
    clone_cmd.extend([build_clone_url(repo_url, access_token), workspace])

    result = subprocess.run(clone_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"git clone failed:\n{result.stderr}")

    return workspace


def resolve_source_path(workspace: str, subdirectory: str | None = None) -> str:
    if not subdirectory:
        return workspace

    workspace_path = Path(workspace).resolve()
    source_path = (workspace_path / subdirectory.strip("/")).resolve()

    if workspace_path not in source_path.parents and source_path != workspace_path:
        raise Exception("Subdirectory must remain inside the cloned repository.")

    if not source_path.exists() or not source_path.is_dir():
        raise Exception(f"Subdirectory does not exist: {subdirectory}")

    return str(source_path)


_NOTEBOOK_LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "r": ".r",
    "julia": ".jl",
    "scala": ".scala",
    "javascript": ".js",
    "typescript": ".ts",
    "ruby": ".rb",
    "go": ".go",
    "java": ".java",
    "c++": ".cpp",
    "c": ".c",
    "csharp": ".cs",
    "php": ".php",
    "bash": ".sh",
    "shell": ".sh",
}


def _notebook_cell_source(cell: dict) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        source = "".join(source)
    return source


def _notebook_language_and_extension(notebook: dict) -> tuple[str, str]:
    """Infer a notebook's kernel language and a matching file extension from its
    metadata (language_info / kernelspec), defaulting to Python when absent."""
    metadata = notebook.get("metadata", {}) or {}
    language_info = metadata.get("language_info", {}) or {}
    kernelspec = metadata.get("kernelspec", {}) or {}

    language = str(language_info.get("name") or kernelspec.get("language") or "python").lower()

    extension = language_info.get("file_extension") or _NOTEBOOK_LANGUAGE_EXTENSIONS.get(language, f".{language}")
    if not extension.startswith("."):
        extension = f".{extension}"

    return language, extension


def _sanitize_magic_lines(text: str) -> str:
    """Comment out IPython line/cell magics and shell escapes (e.g. `%matplotlib
    inline`, `!pip install ...`) so the rest of the cell stays valid Python for
    Semgrep's parser. IPython-only convention - never applied to other kernels,
    where a leading `%`/`!` can be legitimate syntax (e.g. R's `%>%` pipe)."""
    lines = text.split("\n")
    return "\n".join(
        f"# {line}" if line.lstrip().startswith(("%", "!")) else line
        for line in lines
    )


def _notebook_to_source(notebook_path: Path) -> tuple[str, list[tuple[int, int]], str]:
    """Flatten a notebook's code cells into an equivalent source string in its
    kernel's language.

    Returns the generated source, a line_map where line_map[i] gives the
    (cell_index, line_within_cell) that produced generated line i + 1 (so a
    Semgrep finding on the generated file can be traced back to its notebook
    cell), and the file extension to write it with.
    """
    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook = json.load(f)

    language, extension = _notebook_language_and_extension(notebook)
    sanitize = _sanitize_magic_lines if language == "python" else (lambda text: text)

    py_lines: list[str] = []
    line_map: list[tuple[int, int]] = []

    for cell_index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = sanitize(_notebook_cell_source(cell))
        if not source.strip():
            continue
        for local_line, line in enumerate(source.split("\n"), start=1):
            py_lines.append(line)
            line_map.append((cell_index, local_line))
        py_lines.append("")
        line_map.append((cell_index, 0))

    return "\n".join(py_lines), line_map, extension


def convert_notebooks_to_source_files(workspace: str) -> dict[str, list[tuple[int, int]]]:
    """Write a source-code sibling for every notebook in workspace, in its own
    kernel language, so Semgrep - which has no native .ipynb support - picks up
    and scans their code cells.

    Returns a map of generated-file path (relative to workspace) -> line_map, used
    afterwards to translate findings back to notebook cell/line references.
    """
    notebook_maps: dict[str, list[tuple[int, int]]] = {}
    for notebook_path in Path(workspace).rglob("*.ipynb"):
        if NOTEBOOK_CHECKPOINTS_DIR in notebook_path.parts:
            continue
        try:
            source, line_map, extension = _notebook_to_source(notebook_path)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Skipping unreadable notebook {notebook_path}: {exc}")
            continue

        generated_path = notebook_path.with_name(notebook_path.name + extension)
        generated_path.write_text(source, encoding="utf-8")
        notebook_maps[str(generated_path.relative_to(workspace))] = line_map

    return notebook_maps


def _resolve_notebook_location(location: str, line: int | None, notebook_maps: dict) -> tuple[str, int | None]:
    """Translate a finding on a generated `<name>.ipynb<ext>` file back to its
    source notebook and the line within that cell."""
    path = Path(location)
    if not path.stem.endswith(".ipynb") or location not in notebook_maps:
        return location, line

    original = str(path.with_suffix(""))
    line_map = notebook_maps[location]
    if line and 1 <= line <= len(line_map):
        cell_index, cell_line = line_map[line - 1]
        return f"{original} (cell {cell_index + 1})", cell_line or None
    return original, None


def run_semgrep(source_path: str) -> dict:
    """Run Semgrep on source_path and return the taxonomy dict."""
    notebook_maps = convert_notebooks_to_source_files(source_path)
    semgrep_json = os.path.join(source_path, "semgrep.json")
    result = subprocess.run(
        build_semgrep_command(source_path, semgrep_json),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Semgrep warning: {result.stderr}")
    return extract_semgrep_taxonomy(semgrep_json, source_path, notebook_maps)


# ------------------------------
# ENDPOINTS
# ------------------------------

@app.get("/health", tags=["Health"])
def health():
    """Check API health."""
    return {"status": "ok"}


@app.post("/scan", tags=["Scanning"])
async def scan(file: UploadFile = File(...), project_name: str = Form(...)):
    """Upload a file or ZIP and analyze it with Semgrep."""
    project_key = normalize_project_key(project_name)
    workspace = None
    try:
        workspace = prepare_workspace(file, project_key)
        taxonomy = run_semgrep(workspace)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        if workspace and os.path.exists(workspace):
            shutil.rmtree(workspace, ignore_errors=True)

    return {
        "project_key": project_key,
        "project_name": project_name,
        "taxonomy": taxonomy,
    }


@app.post("/scan_with_semgrep", tags=["Scanning"])
async def scan_with_semgrep(file: UploadFile = File(...), project_name: str = Form(...)):
    """Upload a file or ZIP and analyze it with Semgrep (alias of /scan)."""
    return await scan(file=file, project_name=project_name)


@app.post("/scan_github", tags=["Scanning"])
async def scan_github(
    repo_url: str = Form(...),
    project_name: str = Form(...),
    branch: str = Form(None),
    subdirectory: str = Form(None),
    access_token: str = Form(None),
):
    """Clone a GitHub repository and analyze it with Semgrep."""
    project_key = normalize_project_key(project_name)
    workspace = None
    try:
        workspace = prepare_repo_workspace(repo_url, project_key, branch=branch, access_token=access_token)
        source_path = resolve_source_path(workspace, subdirectory)
        taxonomy = run_semgrep(source_path)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        if workspace and os.path.exists(workspace):
            shutil.rmtree(workspace, ignore_errors=True)

    return {
        "project_key": project_key,
        "project_name": project_name,
        "taxonomy": taxonomy,
        "source_type": "github",
    }


@app.post("/scan_github_with_semgrep", tags=["Scanning"])
async def scan_github_with_semgrep(
    repo_url: str = Form(...),
    project_name: str = Form(...),
    branch: str = Form(None),
    subdirectory: str = Form(None),
    access_token: str = Form(None),
):
    """Clone a GitHub repository and analyze it with Semgrep (alias of /scan_github)."""
    return await scan_github(
        repo_url=repo_url,
        project_name=project_name,
        branch=branch,
        subdirectory=subdirectory,
        access_token=access_token,
    )
