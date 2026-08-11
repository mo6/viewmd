"""Gantt chart parser (VIEWMD-0032).

No upstream reference implementation to port from (mermaid-ascii has no gantt
support), so this is hand-written directly against Mermaid's own syntax
(https://mermaid.ai/open-source/syntax/gantt.html), same posture as the
pie/quadrant/packet/kanban parsers.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

GANTT_DIAGRAM_KEYWORD = "gantt"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)(d|w|h)$", re.IGNORECASE)
_STATUS_TOKENS = {"done", "active", "crit", "milestone"}


class ParseError(Exception):
    pass


@dataclass
class Task:
    label: str
    id: str | None
    section: str | None
    done: bool = False
    active: bool = False
    crit: bool = False
    milestone: bool = False
    start: datetime = field(default_factory=datetime.now)
    end: datetime = field(default_factory=datetime.now)


@dataclass
class GanttDiagram:
    title: str = ""
    exclude_weekends: bool = False
    tasks: list[Task] = field(default_factory=list)


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line declares a gantt chart
    (case-insensitive, whole token -- matching er/pie/kanban's own sniff
    convention)."""
    for line in text.split("\n"):
        t = line.strip()
        if t == "":
            continue
        low = t.lower()
        kw = GANTT_DIAGRAM_KEYWORD
        return low == kw or low.startswith(kw + " ")
    return False


@dataclass
class _Pending:
    """A task line's fields, parsed but not yet date-resolved -- resolution
    happens in a second pass (see `_resolve_all`) because `until <id>` may
    reference a task declared *later* in the diagram (D2's `Add to mermaid
    :until isadded`, resolved against `Functionality added` on the next
    line)."""

    label: str
    id: str | None
    section: str | None
    status: set[str]
    start_spec: str | None
    dur_spec: str | None
    lineno: int


def parse(text: str) -> GanttDiagram:
    if not sniff(text):
        raise ParseError(f'expected "{GANTT_DIAGRAM_KEYWORD}" keyword')

    lines = [_strip_comment(ln) for ln in text.strip().split("\n")]

    diagram = GanttDiagram()
    current_section: str | None = None
    seen_keyword = False
    pending: list[_Pending] = []

    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        if line == "":
            continue
        if not seen_keyword:
            seen_keyword = True  # the "gantt" keyword line itself (verified above)
            continue

        low = line.lower()
        if low.startswith("title") and (len(line) == 5 or line[5] in " \t"):
            diagram.title = line[5:].strip()
            continue
        if low.startswith("dateformat") and (len(line) == 10 or line[10] in " \t"):
            fmt = line[10:].strip()
            if fmt != "YYYY-MM-DD":
                raise ParseError(f"line {lineno}: unsupported dateFormat {fmt!r} "
                                  "(only YYYY-MM-DD is supported)")
            continue
        if low.startswith("excludes") and (len(line) == 8 or line[8] in " \t"):
            value = line[8:].strip().lower()
            if value != "weekends":
                raise ParseError(f"line {lineno}: unsupported excludes value {value!r} "
                                  "(only the bare 'excludes weekends' form is supported)")
            diagram.exclude_weekends = True
            continue
        if low.startswith("section") and (len(line) == 7 or line[7] in " \t"):
            current_section = line[7:].strip()
            continue
        if low in ("axisformat", "todaymarker", "weekday", "tickinterval") or any(
            low.startswith(d + " ") or low.startswith(d + ":")
            for d in ("axisformat", "todaymarker", "weekday", "tickinterval")
        ):
            # Layout directives with no ASCII meaning here (Non-goals); skip
            # rather than fail, matching the er parser's styling-line skip.
            continue

        colon = line.find(":")
        if colon < 0:
            raise ParseError(f"line {lineno}: invalid syntax (missing ':'): {line!r}")

        pending.append(_parse_task_fields(
            line[:colon].strip(), line[colon + 1:].strip(), lineno, section=current_section,
        ))

    if not pending:
        raise ParseError("no tasks found")

    diagram.tasks = _resolve_all(pending, diagram.exclude_weekends)
    return diagram


def _strip_comment(line: str) -> str:
    idx = line.find("%%")
    if idx == -1:
        return line
    return line[:idx].rstrip(" \t")


def _parse_task_fields(label: str, rest: str, lineno: int, *, section: str | None) -> _Pending:
    tokens = [t.strip() for t in rest.split(",")]

    status: set[str] = set()
    while tokens and tokens[0].lower() in _STATUS_TOKENS:
        status.add(tokens.pop(0).lower())

    task_id, start_spec, dur_spec = _split_fields(tokens, lineno)
    return _Pending(label=label, id=task_id, section=section, status=status,
                     start_spec=start_spec, dur_spec=dur_spec, lineno=lineno)


def _resolve_all(pending: list[_Pending], exclude_weekends: bool) -> list[Task]:
    """Second pass: compute each task's actual start/end. Deferred from
    parsing (`_parse_task_fields`) because a reference (`after <id>`/`until
    <id>`) or requirement 4a's implicit-continuation default may need another
    task's own resolved dates first -- including, for `until`, one declared
    *later* in the file (see `_Pending`'s docstring). Recursion + memoization
    handles both directions uniformly; a cycle is reported rather than
    looping forever."""
    id_declarations: dict[str, list[int]] = {}
    for i, p in enumerate(pending):
        if p.id:
            id_declarations.setdefault(p.id, []).append(i)

    resolved: dict[int, tuple[datetime, datetime]] = {}
    in_progress: set[int] = set()

    def find_ref(ref_id: str, at_index: int, lineno: int, kw: str) -> int:
        decls = id_declarations.get(ref_id, [])
        if not decls:
            raise ParseError(f"line {lineno}: unknown task id in '{kw} {ref_id}'")
        before = [d for d in decls if d < at_index]
        if before:
            return before[-1]  # requirement 4b: most recent declaration so far
        return decls[0]  # forward reference (D2's "until isadded"); only one exists

    def resolve(i: int) -> tuple[datetime, datetime]:
        if i in resolved:
            return resolved[i]
        if i in in_progress:
            raise ParseError(f"line {pending[i].lineno}: circular task reference")
        in_progress.add(i)
        p = pending[i]

        if p.start_spec is not None and p.start_spec.lower().startswith("until "):
            ref_idx = find_ref(p.start_spec[6:].strip(), i, p.lineno, "until")
            end_dt = resolve(ref_idx)[0]
            if p.dur_spec is None:
                if i == 0:
                    raise ParseError(f"line {p.lineno}: task needs an explicit start "
                                      "(no preceding task to continue from)")
                start_dt = resolve(i - 1)[1]
            elif _DURATION_RE.match(p.dur_spec):
                start_dt = _subtract_duration(end_dt, p.dur_spec, p.lineno, exclude_weekends)
            else:
                raise ParseError(f"line {p.lineno}: 'until' cannot be combined with an "
                                  f"explicit end date ({p.dur_spec!r})")
        else:
            if p.start_spec is None:
                if i == 0:
                    raise ParseError(f"line {p.lineno}: task needs an explicit start "
                                      "(no preceding task to continue from)")
                start_dt = resolve(i - 1)[1]
            elif p.start_spec.lower().startswith("after "):
                ref_idx = find_ref(p.start_spec[6:].strip(), i, p.lineno, "after")
                start_dt = resolve(ref_idx)[1]
            else:
                start_dt = _parse_date(p.start_spec, p.lineno)

            if p.dur_spec is None:
                raise ParseError(f"line {p.lineno}: task needs a duration or end date")
            if _DURATION_RE.match(p.dur_spec):
                end_dt = _add_duration(start_dt, p.dur_spec, p.lineno, exclude_weekends)
            else:
                end_dt = _parse_date(p.dur_spec, p.lineno)

        if "milestone" in p.status:
            end_dt = start_dt  # requirement 5a: point glyph regardless of duration

        in_progress.discard(i)
        resolved[i] = (start_dt, end_dt)
        return resolved[i]

    tasks: list[Task] = []
    for i, p in enumerate(pending):
        start_dt, end_dt = resolve(i)
        tasks.append(Task(
            label=p.label, id=p.id, section=p.section,
            done="done" in p.status, active="active" in p.status,
            crit="crit" in p.status, milestone="milestone" in p.status,
            start=start_dt, end=end_dt,
        ))
    return tasks


def _split_fields(tokens: list[str], lineno: int) -> tuple[str | None, str | None, str | None]:
    """Interpret the (status-stripped) comma-separated remainder of a task
    line as (id, start, duration|end), any of which may be implicit per
    requirement 4a/4."""
    if len(tokens) == 0:
        raise ParseError(f"line {lineno}: task missing start/duration fields")
    if len(tokens) == 1:
        tok = tokens[0]
        if _DURATION_RE.match(tok):
            return None, None, tok  # implicit start (4a), explicit duration
        if tok.lower().startswith("until "):
            return None, tok, None  # implicit start, until-bounded end
        if tok.lower().startswith("after "):
            raise ParseError(f"line {lineno}: 'after' start requires a duration or end date")
        raise ParseError(f"line {lineno}: cannot parse task fields: {tok!r}")
    if len(tokens) == 2:
        a, b = tokens
        if _looks_like_start(a):
            return None, a, b
        return a, None, b  # a is an id; implicit start (4a)
    if len(tokens) == 3:
        return tokens[0], tokens[1], tokens[2]
    raise ParseError(f"line {lineno}: too many fields in task line: {tokens!r}")


def _looks_like_start(tok: str) -> bool:
    low = tok.lower()
    return bool(_DATE_RE.match(tok)) or low.startswith("after ") or low.startswith("until ")


def _parse_date(s: str, lineno: int) -> datetime:
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ParseError(f"line {lineno}: invalid date {s!r} (expected YYYY-MM-DD)") from exc


def _add_duration(start: datetime, dur_spec: str, lineno: int, exclude_weekends: bool) -> datetime:
    m = _DURATION_RE.match(dur_spec)
    if m is None:
        raise ParseError(f"line {lineno}: invalid duration {dur_spec!r}")
    amount = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "h":
        return start + timedelta(hours=amount)
    days = amount * 7 if unit == "w" else amount
    return _shift_days(start, days, exclude_weekends)


def _subtract_duration(
    end: datetime, dur_spec: str, lineno: int, exclude_weekends: bool,
) -> datetime:
    m = _DURATION_RE.match(dur_spec)
    if m is None:
        raise ParseError(f"line {lineno}: invalid duration {dur_spec!r}")
    amount = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "h":
        return end - timedelta(hours=amount)
    days = amount * 7 if unit == "w" else amount
    return _shift_days(end, -days, exclude_weekends)


def _shift_days(start: datetime, days: float, exclude_weekends: bool) -> datetime:
    """Shift `start` by `days` (may be negative), optionally skipping
    Saturday/Sunday (requirement 8) -- weekend days are stepped over without
    counting against the day budget, calendar-day math otherwise."""
    if not exclude_weekends or days == 0:
        return start + timedelta(days=days)
    sign = 1 if days > 0 else -1
    whole = int(abs(days))
    frac = abs(days) - whole
    cur = start
    remaining = whole
    while remaining > 0:
        cur += timedelta(days=sign)
        if cur.weekday() < 5:  # Mon-Fri
            remaining -= 1
    cur += timedelta(days=sign * frac)
    return cur


def round_half_up(x: float) -> int:
    return math.floor(x + 0.5)
