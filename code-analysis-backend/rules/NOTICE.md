# Third-party Semgrep rules

The code analysis backend scans with the rules in this folder only. It does not download rule sets from the
Semgrep registry, because the registry mixes licences (see "Why not the registry" below).

This project is licensed **AGPL-3.0-or-later** (see `LICENSE` at the repository root). Every licence below is
open source, allows commercial use (including charging for a hosted service) and is compatible with
AGPL-3.0-or-later. None of them requires a payment.

## Sources

### GitLab SAST rules

[GitLab SAST rules](https://gitlab.com/gitlab-org/security-products/sast-rules), release **v2.10.2**
(commit `83144bd2ec7d3200cda96347fa923f81c8ad8413`). The `rule-*.yml` files are copied unchanged, with their
original per-file licence header (the test fixtures of the upstream repository are not included).

| Folder | Rules licence | Languages | Original source | Full text |
|---|---|---|---|---|
| `python/`, `javascript/`, `java/`, `scala/`, `csharp/` | MIT, (c) GitLab Inc. | Python, JS/TS, Java, Scala, C# | GitLab | `LICENSE-sast-rules-MIT.txt` |
| `go/` | Apache-2.0, (c) gosec (26 files), MIT (1 file) | Go | [gosec](https://github.com/securego/gosec) | `LICENSE-Apache-2.0.txt` |
| `c/` | GPL-2.0-or-later | C, C++ | [flawfinder](https://github.com/david-a-wheeler/flawfinder) | `LICENSE-GPL-2.0.txt` |
| `lgpl/` | LGPL-3.0 | Java, JS, Kotlin, Swift, Objective-C | [njsscan](https://github.com/ajinabraham/njsscan), [mobsfscan](https://github.com/mobsf/mobsfscan), [Find Security Bugs](https://find-sec-bugs.github.io) | `LICENSE-LGPL-3.0.txt` (needs `LICENSE-GPL-3.0.txt`, also included) |

Every file keeps its own `# License:` header; keep it when you copy or modify a rule.

### Trail of Bits Semgrep rules (`trailofbits/`)

[trailofbits/semgrep-rules](https://github.com/trailofbits/semgrep-rules), commit
`31390b3` (2025-11-12), licensed **AGPL-3.0** (the same licence as this project): 120 rules for Python and machine
learning code (unsafe pickles in pandas, PyTorch, Keras, NumPy, scikit-learn), insecure container, TLS and
`curl`/`wget` flags (`generic/`), YAML (Ansible, Docker Compose, Kubernetes), Terraform (`hcl/`), Go, JavaScript,
Ruby, Java/Kotlin, Swift and Rust. Only the rule files (`*.yaml`) are copied, unchanged; the example files next to
them in the upstream repository ("may be derived from other works", per its README) and the `*.test.yaml` files are
not included. These files have no per-file header: their licence is the one of the upstream repository.

One rule is left out on purpose: `python/automatic-memory-pinning.yaml` warns on every PyTorch `DataLoader` that does
not set `pin_memory`. The rule itself rates it low likelihood and low impact (a performance suggestion), but it is
shown as a warning and fires once per `DataLoader`, which buries real findings. When you update this folder, do not
copy it back.

## What each licence asks of you

| Licence | Obligations |
|---|---|
| MIT | Keep the copyright and permission notice in copies. |
| Apache-2.0 | Keep the licence text and the copyright and attribution notices; mark files you modify. |
| GPL-2.0-or-later (`c/`) | When you distribute the rules, keep them under the GPL with the licence text. The flawfinder source states "version 2 or (at your option) any later version", which is what lets them be part of an AGPL-3.0 project. |
| LGPL-3.0 (`lgpl/`) | Keep the licence texts and notices; release modifications of these rule files under LGPL-3.0. |
| AGPL-3.0 (`trailofbits/`) | Same licence as this project: keep the notices and offer the source of modified versions to the users of a service you run. |
| AGPL-3.0-or-later (this project) | Anyone who runs a modified version as a network service must offer its source to the users of that service. |

## Original rules of this project (`custom/`)

The rules in `custom/` were written for this project and are licensed AGPL-3.0-or-later (each file carries an
`SPDX-License-Identifier` header). They cover what the third-party rules above do not:

| Rule | What it finds |
|---|---|
| `javascript/rule-browser-storage-password.yml` | A password written to `localStorage` / `sessionStorage` (CWE-312) |
| `javascript/rule-browser-storage-token.yml` | An access token or key written to browser storage (CWE-922, info) |
| `javascript/rule-cors-wildcard.yml`, `python/rule-cors-wildcard.yml` | CORS that allows any origin (CWE-942); an error when credentials are also allowed |
| `dockerfile/rule-missing-user.yml` | A Dockerfile that never sets `USER`, so the container runs as root (CWE-250) |
| `secrets/rule-hardcoded-credentials.yml` | Passwords, secrets and keys assigned as string literals in Python, JS/TS and Java (CWE-798) |
| `python/rule-file-never-closed.yml` | A file opened inside a call and never closed, such as `yaml.safe_dump(x, open(...))` (CWE-775, info) |
| `python/rule-warnings-ignore-all.yml` | All Python warnings switched off (info) |
| `python/rule-pip-install-unpinned.yml` | Packages installed at run time without a pinned version, including `%pip install` and `!pip install` in notebooks (info) |
| `secrets/rule-secret-tokens.yml` | Well-known key formats (AWS, Google, GitHub, Slack, Stripe, SonarQube), private keys and URLs with a password (CWE-798, CWE-321) |

The token patterns follow the publicly documented formats of each provider; they are not copied from other rule
sets. Test them with Semgrep's own runner: `semgrep --test rules/custom` (the token rules have no fixture files on
purpose, because realistic-looking keys trigger secret scanners such as GitHub push protection). Raw `*.ipynb`
files are excluded from the secret rules: the code cells are scanned after conversion, which gives a cell number.

## Not included, on purpose

These parts of the same upstream repository cannot be used for an open-source project that offers a paid service:

| Upstream path | Licence | Why it is excluded |
|---|---|---|
| `rules/lgpl-cc/` | LGPL-2.1 + Commons Clause (Semgrep, Inc.) | The Commons Clause removes the right to "Sell" the software, including offering a paid service whose value comes substantially from it |
| `rules/gitlab/` | GitLab Enterprise Edition licence | Needs a paid GitLab subscription and forbids publishing the files |

## Why not the Semgrep registry (`p/...` rule sets)

Rules written by Semgrep (for example `p/python`, `p/owasp-top-ten`, `p/gitleaks`, and the `python.*` and `java.*`
rules inside `p/bandit` and `p/findsecbugs`) are under the *Semgrep Rules License v1.0*:
"You may use the rules only for your own internal business purposes", and the licence "does not allow you to
distribute the rules, or to make them available to others as a service"
(<https://semgrep.dev/legal/rules-license>). Offering code analysis to platform users is such a service.
The licence shown in the registry metadata is also not always reliable: `p/flawfinder` labels its rules MIT while
the rule files say GPL-2.0. Check the header of each file.

The Semgrep engine itself (the `semgrep` command, LGPL-2.1) is a separate program that is run as a subprocess; it
is not part of this folder.

This note is a technical summary, not legal advice.

## Updating

1. Pick a release tag of the upstream repository and copy `rule-*.yml` from the folders in the table above only.
   Upstream, `lgpl/` is at `rules/lgpl/`; the other folders are at the top level. For `trailofbits/`, copy the
   `*.yaml` rule files only (not the example files and not `*.test.yaml`).
2. Check that every copied file has an allowed `# License:` line:
   `grep -rL "^# \(License: \(License: \)\?\(MIT\|Apache 2.0\|GPL 2.0\|GNU Lesser General Public License v3.0\)\|SPDX-License-Identifier: AGPL-3.0-or-later\)" rules --include='rule-*.yml'`
   must print nothing (one upstream `go/` file has a doubled `License: License: MIT` prefix).
3. Update the release and commit above.
