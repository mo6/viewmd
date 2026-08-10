# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in viewmd, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email gmo6nl@gmail.com or use GitHub's private vulnerability reporting feature.

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

### Response Timeline

viewmd is a personal project maintained without any SLA or availability guarantee. Reports are
handled on a best-effort basis: no committed acknowledgment window, no committed fix timeline.
Severity still shapes priority — a report with a working exploit and reproduction steps gets
looked at sooner than a theoretical one.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Attack Surface

viewmd renders Markdown text to ANSI and pages it. There is no network access anywhere in the
tool, and no content from a rendered `.md` file is ever executed — Markdown is rendered as text,
never as code. The one subprocess call is the pager (`$PAGER`, default `less -R -F -X`); its
argv comes from the `$PAGER` environment variable or the fixed default, never from parsed
Markdown content. Front-matter and wikilink parsing are regex/string-based only — no `eval`, no
dynamic import, no YAML deserialization.

Every `./run-tests.sh` run also gates on static-analysis (`ruff` with Bandit-compatible `S`
rules) and known-CVE checks (`pip-audit`) before a change can land — see
[docs/SECURITY.md](docs/SECURITY.md) for that gate's full runbook, scope, and standing
exceptions.

## Security Best Practices

When using viewmd:

- Only render trusted Markdown files
- Be cautious when piping content from untrusted sources
- Keep your installation up to date
- Remember the pager and your `$EDITOR`/`$PAGER` binary are out of scope for this project's own
  checks — viewmd hands them already-rendered text, but what they do with it is between you and
  that binary
