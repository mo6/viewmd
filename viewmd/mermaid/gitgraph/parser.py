"""gitGraph parser (VIEWMD-0042).

No upstream reference implementation to port from (the local mermaid-ascii Go
oracle used to differential-test the flowchart/sequence/ER ports has no
gitGraph support at all), so this is hand-written directly against Mermaid's
own gitGraph syntax (https://mermaid.js.org/syntax/gitgraph.html), same
posture as the pie/quadrant/kanban parsers.

Parsing is a straight statement replay (see the issue's design notes):
`commit`/`branch`/`checkout`/`merge`/`cherry-pick` are executed in source
order against a `{branch_name: row}` table plus a `current_branch` pointer, a
single shared timeline column counter incremented on every `commit`/`merge`/
`cherry-pick`, and a global `commit_id -> branch_row` table so a `merge`/
`cherry-pick` can reference a commit on any lane, not just the current one.
Only the default left-right orientation is supported -- `gitGraph TB:`/
`BT:`/`RL:` is unsupported input for this issue (falls back to the raw
fence), not a silent re-render as LR.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import remove_comments, split_lines

GITGRAPH_DIAGRAM_KEYWORD = "gitGraph"

# The bare `gitGraph` keyword, optionally followed by an orientation
# directive (`TB:`/`BT:`/`RL:`/`LR:`) -- only the implicit default (no
# directive, or an explicit `LR:`) is supported by this issue.
_HEADER_RE = re.compile(r"(?i)^\s*gitgraph\s*(?:(tb|bt|rl|lr)\s*:)?\s*$")

_BRANCH_RE = re.compile(r"^branch\s+(\S+)\s*$")
_CHECKOUT_RE = re.compile(r"^(?:checkout|switch)\s+(\S+)\s*$")
_COMMIT_RE = re.compile(r"^commit\b(.*)$")
_MERGE_RE = re.compile(r"^merge\s+(\S+)\b(.*)$")
_CHERRY_PICK_RE = re.compile(r"^cherry-pick\b(.*)$")
_ATTR_RE = re.compile(r'(\w+)\s*:\s*"([^"]*)"')


class ParseError(Exception):
    pass


@dataclass
class GitCommit:
    id: str
    column: int
    label: str  # the text drawn beneath the marker (the commit id, or "<id>-cherry")
    tag: str | None = None


@dataclass
class GitConnector:
    """A vertical connector between two lanes at a single timeline column,
    drawn wherever a `branch`, `merge`, or `cherry-pick` crosses lanes.
    `owner_row` is the lane that received the new commit at `column` (already
    drawn as a marker); `other_row` is the lane it connects back to (drawn as
    a passthrough junction)."""

    owner_row: int
    other_row: int
    column: int


@dataclass
class GitBranch:
    name: str
    row: int
    commits: list[GitCommit] = field(default_factory=list)
    # Set by `branch <name>` to the parent lane's row until this branch's
    # first commit lands (the visual branch point where the connector back to
    # the parent is actually drawn); None once resolved, or for `main`
    # (which has no parent).
    pending_parent_row: int | None = None


@dataclass
class GitGraph:
    branches: list[GitBranch] = field(default_factory=list)
    connectors: list[GitConnector] = field(default_factory=list)


def _has_gitgraph_keyword(line: str) -> bool:
    lower = line.strip().lower()
    kw = GITGRAPH_DIAGRAM_KEYWORD.lower()
    if not lower.startswith(kw):
        return False
    rest = lower[len(kw):]
    return rest == "" or rest[0] in (" ", "\t", ":")


def sniff(text: str) -> bool:
    """Whether `text` opens with the gitGraph keyword (ignoring blank lines
    and %% comments)."""
    for line in text.split("\n"):
        trimmed = line.strip()
        if trimmed == "" or trimmed.startswith("%%"):
            continue
        return _has_gitgraph_keyword(trimmed)
    return False


def parse(text: str) -> GitGraph:
    text = text.strip()
    if not text:
        raise ParseError("empty input")

    raw_lines = split_lines(text)
    lines = remove_comments(raw_lines)
    if not lines:
        raise ParseError("no content found")

    header = lines[0].strip()
    m = _HEADER_RE.match(header)
    if m is None:
        raise ParseError('expected "gitGraph" keyword')
    orientation = (m.group(1) or "lr").lower()
    if orientation != "lr":
        # TB/BT/RL are explicitly out of scope for this issue (Non-goals) --
        # unsupported input, falls back to the raw fence like a syntax error.
        raise ParseError(f'gitGraph "{orientation.upper()}:" orientation is not supported')
    lines = lines[1:]

    graph = GitGraph()
    branch_by_name: dict[str, GitBranch] = {}
    commit_owner: dict[str, int] = {}  # commit id -> branch row, for cross-lane references

    def _add_branch(name: str) -> GitBranch:
        b = GitBranch(name=name, row=len(graph.branches))
        graph.branches.append(b)
        branch_by_name[name] = b
        return b

    main = _add_branch("main")
    current = main
    column = 0

    for i, line in enumerate(lines):
        trimmed = line.strip()
        if trimmed == "":
            continue
        lineno = i + 2

        m = _BRANCH_RE.match(trimmed)
        if m is not None:
            name = m.group(1)
            if name in branch_by_name:
                raise ParseError(f'line {lineno}: branch "{name}" already exists')
            parent = current
            current = _add_branch(name)
            # The connector back to the parent lane is only known once this
            # branch's first commit lands (that column is the visual branch
            # point) -- recorded lazily by _resolve_pending_parent below.
            current.pending_parent_row = parent.row
            continue

        m = _CHECKOUT_RE.match(trimmed)
        if m is not None:
            name = m.group(1)
            target = branch_by_name.get(name)
            if target is None:
                raise ParseError(f'line {lineno}: checkout of undeclared branch "{name}"')
            current = target
            continue

        m = _COMMIT_RE.match(trimmed)
        if m is not None:
            attrs = dict(_ATTR_RE.findall(m.group(1)))
            id_ = attrs.get("id")
            if not id_:
                id_ = _random_commit_id(commit_owner)
            if id_ in commit_owner:
                raise ParseError(f'line {lineno}: duplicate commit id "{id_}"')
            gc = GitCommit(id=id_, column=column, label=id_, tag=attrs.get("tag"))
            current.commits.append(gc)
            commit_owner[id_] = current.row
            _resolve_pending_parent(graph, current, gc.column)
            column += 1
            continue

        m = _MERGE_RE.match(trimmed)
        if m is not None:
            name = m.group(1)
            target = branch_by_name.get(name)
            if target is None:
                raise ParseError(f'line {lineno}: merge of undeclared branch "{name}"')
            attrs = dict(_ATTR_RE.findall(m.group(2)))
            id_ = attrs.get("id", "")
            if id_ and id_ in commit_owner:
                raise ParseError(f'line {lineno}: duplicate commit id "{id_}"')
            gc = GitCommit(id=id_, column=column, label=id_)
            current.commits.append(gc)
            if id_:
                commit_owner[id_] = current.row
            _resolve_pending_parent(graph, current, gc.column)
            graph.connectors.append(
                GitConnector(owner_row=current.row, other_row=target.row, column=column)
            )
            column += 1
            continue

        m = _CHERRY_PICK_RE.match(trimmed)
        if m is not None:
            attrs = dict(_ATTR_RE.findall(m.group(1)))
            source_id = attrs.get("id")
            if not source_id:
                raise ParseError(f'line {lineno}: "cherry-pick" requires an id: attribute')
            source_row = commit_owner.get(source_id)
            if source_row is None:
                raise ParseError(
                    f'line {lineno}: cherry-pick of undeclared commit id "{source_id}"'
                )
            gc = GitCommit(id="", column=column, label=f"{source_id}-cherry")
            current.commits.append(gc)
            _resolve_pending_parent(graph, current, gc.column)
            graph.connectors.append(
                GitConnector(owner_row=current.row, other_row=source_row, column=column)
            )
            column += 1
            continue

        raise ParseError(f'line {lineno}: invalid syntax: "{trimmed}"')

    if not any(b.commits for b in graph.branches):
        raise ParseError("no commits found")

    return graph


def _random_commit_id(commit_owner: dict[str, int]) -> str:
    """A random 4-hex-char id for a bare `commit` (no `id:` attribute) --
    Mermaid itself auto-generates one in this case
    (https://mermaid.js.org/syntax/gitgraph.html); collisions against
    already-assigned ids (random or explicit) are re-rolled, vanishingly
    unlikely in practice but cheap to guard against exactly."""
    while True:
        candidate = f"{random.randrange(16**4):04x}"  # noqa: S311 -- cosmetic id, not security
        if candidate not in commit_owner:
            return candidate


def _resolve_pending_parent(graph: GitGraph, branch: GitBranch, column: int) -> None:
    """If `branch` was created by a `branch` statement whose connector back to
    its parent lane hasn't been drawn yet, this is its first commit -- the
    visual branch point -- so record the connector now and clear the pending
    marker."""
    parent_row = branch.pending_parent_row
    if parent_row is None:
        return
    graph.connectors.append(
        GitConnector(owner_row=branch.row, other_row=parent_row, column=column)
    )
    branch.pending_parent_row = None
