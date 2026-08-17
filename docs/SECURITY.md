# Security gate

For how to report a vulnerability, see [../SECURITY.md](../SECURITY.md). This file is the
maintainer-facing runbook for the automated checks below, not the disclosure policy.

**Status: implemented (1.1.0).** A maintainer-facing gate, not a certification. It asks two
questions every `./run-tests.sh` run: are there common insecure patterns in our Python, and are
any installed packages known-vulnerable? [VIEWMD-0009](../issues/archive/VIEWMD-0009-security-gate.md)
is the testable *what*; this essay is the *why* and the runbook.

Green here means the checklist below passed. It does not mean viewmd's output can be trusted as
a substitute for reading the source `.md` file yourself. Those limits stay in section 6.

---

## 1. Purpose

Catch regressions that are cheap for a tool to see and expensive for a human to rediscover:

- insecure call shapes (`eval`, `shell=True`, weak hashes, …) via ruff's Bandit-compatible `S` rules;
- known CVEs in the venv via `pip-audit` (PyPA advisory database).

Fix first. Suppress only when the finding is an accepted, documented risk, and keep the ignore
narrow.

## 2. Attack surface

viewmd's surface is small by construction: it renders Markdown text to ANSI and pages it, entirely
in-process (VIEWMD-0072: no external pager subprocess, `$PAGER` is not read anywhere). There is no
network access anywhere in the tool, and no content from a rendered `.md` file is ever executed --
Rich renders Markdown as text, never as code (docs/PLAN.md's "HTML rendering" section).

| Surface | Where | Notes |
|---|---|---|
| File / stdin reading | `viewmd/__main__.py` | Reads the path given on the command line, or stdin, as UTF-8 text. No execution, no templating. |
| Config-file reading | `viewmd/config.py` | Reads a UTF-8 `key = value` file from an XDG path, `--config PATH`, or not at all (`VIEWMD_NO_CONFIG`). No execution, no interpolation, no includes. |
| Front-matter / wikilink parsing | `viewmd/frontmatter.py`, `viewmd/wikilinks.py` | Regex- and string-based text parsing only; no `eval`, no dynamic import, no YAML deserialization (deliberately not a full YAML parser -- docs/PLAN.md). |

Out of scope for this gate: the terminal emulator and the host OS.

## 3. Tools in `./run-tests.sh`

| Step | Tool | Network | Scans |
|---|---|---|---|
| `ruff` | ruff with `select` including `S` | offline | `viewmd/`, `tests/`, `tools/` |
| `pip-audit` | `python -m pip_audit` | **needs** advisory data | packages installed in `.venv` |

Run in isolation while debugging:

```sh
.venv/bin/ruff check .
.venv/bin/python -m pip_audit --progress-spinner off
```

`pip-audit` is a `[dev]` extra (`pip install -e '.[dev]'`). It audits the **installed**
environment (the same one the gate uses). There is no lock file today; if one is added later,
point the audit at it and update this section.

**Fetch failure is a failed step.** If advisory data cannot be downloaded, `pip-audit` exits
non-zero. That is intentional: the gate must not report success when it could not check. There is
no silent skip and no "offline means clean" path. Re-run with network, or fix connectivity.

## 4. Findings lifecycle

1. The gate fails and names a ruff rule id (`S###`) or a `pip-audit` advisory id.
2. **Prefer a fix:** change the call shape, or bump the package constraint in `pyproject.toml` and
   refresh the venv.
3. **Suppress only if accepted:** a narrow `per-file-ignores` entry or a single-line `# noqa: S###`
   with a short reason comment. For advisories, ignore by package + advisory id only, with a
   reason in this file.
4. Update the standing-exceptions table below in the same change.
5. Never `ignore = ["S"]` (or any blanket disable of the security set) in `pyproject.toml`.

Severity policy: every non-suppressed `S` finding and every non-ignored advisory fails the gate.

## 5. Standing exceptions

Canonical config: `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`. Reasons live here so
config stays short.

| Location | Rule | Reason |
|---|---|---|
| `tests/**` | `S101` | pytest uses `assert`; not a production assert-as-control-flow smell. |
| `tools/**` | `S101`, `S603`, `S607` | Maintainer tooling (`tools/issues.py`): fixed argv lists, no shell, no attacker-controlled executable name. Its own `assert`-based checks use the same idiom as tests. |

No `pip-audit` ignores at 1.1.0. When one is needed, add a row here (package, advisory id,
reason) and the matching ignore flag/config beside the `pip-audit` step.

## 6. What green does not mean

- **Front-matter and wikilink parsing are intentionally not full parsers** (docs/PLAN.md): a
  value that doesn't fit the flat shape renders as its raw string rather than failing, which is a
  correctness choice, not a security boundary being asserted.
- **This gate does not review Markdown content itself.** viewmd renders whatever `.md` file it's
  given; judging that content is the reader's job, not the tool's.

## 7. Cadence

- Every `./run-tests.sh` (Definition of Done in [issues/AGILE.md](../issues/AGILE.md)).
- Re-read this essay when adding a `subprocess` call, a new runtime or `[dev]` dependency, or a
  standing suppression.
- Secrets scanning and hosted CI are deferred; revisit when there is a real secret surface or a
  remote CI runner.
