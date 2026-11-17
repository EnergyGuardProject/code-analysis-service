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

## Semgrep rules
Findings come from the rules vendored in [`rules/`](rules/): the [GitLab SAST rules](https://gitlab.com/gitlab-org/security-products/sast-rules) (release v2.10.2) for Python, JavaScript/TypeScript, Java, Kotlin, Scala, C/C++, C#, Go, Swift and Objective-C. They are licensed MIT, Apache-2.0, GPL-2.0-or-later or LGPL-3.0, which are open-source licences that allow commercial use and are compatible with this project's AGPL-3.0-or-later licence. The scan needs no internet access and does not download rules from the Semgrep registry.

Do **not** add registry rule sets (`p/...`): many of their rules are under the Semgrep Rules License, which does not allow offering them to others as a service. [`rules/NOTICE.md`](rules/NOTICE.md) lists the sources, the licences, the obligations of each, what is left out (Commons Clause and proprietary rules) and how to update the rules.

[`rules/trailofbits/`](rules/trailofbits/) adds the AGPL-3.0 rules of [Trail of Bits](https://github.com/trailofbits/semgrep-rules): unsafe pickles in machine-learning code, insecure container, TLS and `curl` flags, Docker Compose, Kubernetes and Terraform files.

On top of those, [`rules/custom/`](rules/custom/) holds original rules of this project (AGPL-3.0-or-later) for what the other sets miss: hard-coded passwords and well-known key formats, passwords or tokens saved in the browser storage, wildcard CORS, Dockerfiles that run as root, files never closed, silenced warnings and unpinned `pip install`. Test them with `semgrep --test rules/custom`.

Notebooks (`.ipynb`) are converted to source files cell by cell before the scan (IPython magics such as `%pip install x` become the `get_ipython()` calls IPython would run), so findings point to a cell and a line; the raw notebook JSON is excluded from the scan.

Not covered at the moment: PHP, and application logic that no pattern can express. "Files scanned" counts the text files the rules read (code, configuration, Dockerfiles); raw notebooks are scanned through their converted code cells.

## Response format
All scan endpoints return a JSON object with a `taxonomy` key containing:
- `cwe` / `cve` — sorted lists of detected identifiers
- `incidents` — per-finding details (rule, message, location, severity, CWE refs)
- `standards` — deduplicated standard rows for display
- `by_rule` — metadata grouped by Semgrep rule ID
- `stats` — `files_scanned`, `findings_total`, `scan_time_sec`
- `scanned_files` — normalized list of scanned file paths
- `scan_errors` — files Semgrep could not (fully) analyze, e.g. because of a syntax error: `location` (notebooks: `file.ipynb (cell N)`), `line`, `type`, `level`, `message`. Semgrep skips such files without failing, so an empty `incidents` list is only a clean result when `scan_errors` is empty too. `stats.files_with_errors` counts the affected files.

If Semgrep produces no report at all, the endpoints return HTTP 500 with an `error` message instead of an empty result.

## Notes
- Workspaces are created under `/tmp/<project_key>` and cleaned after each request.
- If you change dependencies, rebuild the image.
