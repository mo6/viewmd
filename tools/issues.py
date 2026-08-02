#!/usr/bin/env python3
"""Index and lint the issues/ tree.

    python tools/issues.py            # rebuild the index table in issues/README.md
    python tools/issues.py --check    # lint + assert the index is current; write nothing

Not part of the viewmd package and not imported by it. Stdlib only: the front matter is a small,
fixed shape, so it is parsed by hand rather than pulling in a YAML dependency.

What --check enforces, gathering every problem before it exits (so one run reports them all):

  - every VIEWMD-NNNN-slug.md has the required front-matter keys, and its id matches its filename;
  - ids are unique and contiguous from VIEWMD-0001;
  - status is one of the known values, and the file sits in the directory that status implies
    (implemented/superseded -> archive/, rejected -> rejected/, proposed/in-progress -> root);
  - implemented/superseded carry >=1 commit; proposed/in-progress/rejected carry none;
  - in-progress/implemented/superseded carry effort and accepted_by/accepted_at (the Definition
    of Ready gate, AGILE.md);
  - the generated index block in README.md is up to date.

Exit status is non-zero if any check fails, so it drops straight into ./run-tests.sh.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "issues"
README = ISSUES_DIR / "README.md"

REQUIRED_KEYS = ["id", "title", "status", "area", "effort", "created", "updated",
                  "accepted_by", "accepted_at", "commits", "related", "supersedes"]
STATUSES = {"proposed", "in-progress", "implemented", "superseded", "rejected"}
SHIPPED = {"implemented", "superseded"}          # these must carry commits
GATED = {"in-progress", "implemented", "superseded"}  # these must carry effort + acceptance
EFFORTS = {"low", "medium", "high"}

START, END = "<!-- issues:index:start -->", "<!-- issues:index:end -->"
NAME_RE = re.compile(r"^VIEWMD-(\d{4})-[a-z0-9-]+\.md$")


def parse_front_matter(path: pathlib.Path) -> dict:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")
    end = text.index("\n---\n", 4)
    block = text[4:end]
    data: dict[str, object] = {}
    for line in block.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.split("#", 1)[0].strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [v.strip() for v in inner.split(",") if v.strip()] if inner else []
        else:
            data[key] = value
    return data


def find_issues() -> list[pathlib.Path]:
    files = []
    for sub in (ISSUES_DIR, ISSUES_DIR / "archive", ISSUES_DIR / "rejected"):
        if sub.exists():
            files.extend(sorted(p for p in sub.glob("VIEWMD-*.md")))
    return files


def lint(files: list[pathlib.Path]) -> list[str]:
    problems = []
    seen_ids: dict[str, pathlib.Path] = {}
    for path in files:
        name_match = NAME_RE.match(path.name)
        if not name_match:
            problems.append(f"{path}: filename does not match VIEWMD-NNNN-slug.md")
            continue
        try:
            data = parse_front_matter(path)
        except ValueError as e:
            problems.append(str(e))
            continue

        missing = [k for k in REQUIRED_KEYS if k not in data]
        if missing:
            problems.append(f"{path}: missing front-matter keys: {', '.join(missing)}")
            continue

        file_id = f"VIEWMD-{name_match.group(1)}"
        if data["id"] != file_id:
            problems.append(f"{path}: id {data['id']!r} does not match filename ({file_id})")
        if data["id"] in seen_ids:
            problems.append(f"{path}: duplicate id {data['id']!r} (also {seen_ids[data['id']]})")
        seen_ids[data["id"]] = path

        status = data["status"]
        if status not in STATUSES:
            problems.append(f"{path}: unknown status {status!r}")
            continue

        parent = path.parent.name
        expect_dir = {"implemented": "archive", "superseded": "archive",
                      "rejected": "rejected"}.get(status, "issues")
        actual_dir = parent if parent in ("archive", "rejected") else "issues"
        if actual_dir != expect_dir:
            problems.append(
                f"{path}: status {status!r} belongs in {expect_dir}/, found in {actual_dir}/"
            )

        commits = data["commits"]
        if status in SHIPPED and not commits:
            problems.append(f"{path}: status {status!r} requires at least one commit")
        if status not in SHIPPED and commits:
            problems.append(f"{path}: status {status!r} must not carry commits")

        if status in GATED:
            if data.get("effort") not in EFFORTS:
                problems.append(f"{path}: status {status!r} requires effort: low|medium|high")
            if not data.get("accepted_by") or not data.get("accepted_at"):
                problems.append(f"{path}: status {status!r} requires accepted_by and accepted_at")

    ids_numeric = sorted(int(i.removeprefix("VIEWMD-")) for i in seen_ids)
    for expected, actual in enumerate(ids_numeric, start=1):
        if expected != actual:
            problems.append(
                f"issues: id sequence has a gap or is non-contiguous at VIEWMD-{expected:04d}"
            )
            break

    return problems


def build_index(files: list[pathlib.Path]) -> str:
    rows = []
    for path in files:
        try:
            data = parse_front_matter(path)
        except ValueError:
            continue
        location = "archive/" if path.parent.name == "archive" else \
                   "rejected/" if path.parent.name == "rejected" else ""
        rows.append((data.get("id", "?"), data.get("status", "?"),
                     data.get("title", "?"), f"{location}{path.name}"))
    rows.sort(key=lambda r: r[0])

    lines = ["| id | status | title |", "| --- | --- | --- |"]
    for issue_id, status, title, rel in rows:
        lines.append(f"| [{issue_id}]({rel}) | {status} | {title} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                         help="lint + assert the index is current; write nothing")
    args = parser.parse_args(argv)

    files = find_issues()
    problems = lint(files)
    if problems:
        for p in problems:
            print(f"issues: {p}", file=sys.stderr)

    readme_text = README.read_text()
    start_i = readme_text.index(START) + len(START)
    end_i = readme_text.index(END)
    current_block = readme_text[start_i:end_i].strip("\n")
    new_block = build_index(files)
    new_readme = readme_text[:start_i] + "\n" + new_block + "\n" + readme_text[end_i:]

    if args.check:
        if current_block != new_block:
            print("issues: index in README.md is stale; run ./tools.sh issues", file=sys.stderr)
            problems.append("stale index")
        return 1 if problems else 0

    if current_block != new_block:
        README.write_text(new_readme)
        print("issues: index regenerated")
    else:
        print("issues: index already current")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
