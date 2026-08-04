"""Sequence-diagram parser, ported from pkg/sequence/parser.go."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto

from viewmd.mermaid.textutil import remove_comments, split_lines

SEQUENCE_DIAGRAM_KEYWORD = "sequenceDiagram"

# --- regexes, transcribed 1:1 from parser.go ---

_PARTICIPANT_RE = re.compile(
    r'(?i)^\s*(?:participant|actor)\s+(?:"([^"]+)"|(\S+))(?:\s+as\s+(.+))?$'
)
# Which keyword introduced the declaration, checked separately so the capture
# groups _parse_participant relies on stay untouched (VIEWMD-0017).
_ACTOR_KEYWORD_RE = re.compile(r"(?i)^\s*actor\b")
# The arrow is one of mermaid's ten message types: ->> / -->> (arrowhead), ->
# / --> (open), -x / --x (cross), -) / --) (async point), <<->> / <<-->>
# (bidirectional). Longer alternatives come first so e.g. "-->>" is never
# consumed as "-->". An optional "()" on either side of the arrow marks a
# central connection: a circle where the message meets that lifeline.
_MESSAGE_RE = re.compile(
    r'^\s*(?:"([^"]+)"|([^\s<>(-]+))\s*(\(\))?\s*'
    r"(<<-->>|<<->>|-->>|--[x)]|-->|->>|-[x)]|->)\s*(\(\))?\s*"
    r'(?:"([^"]+)"|([^\s<>(-]+))\s*:\s*(.*)$'
)
_AUTONUMBER_RE = re.compile(r"(?i)^\s*autonumber\s*$")
_FRAGMENT_START_RE = re.compile(r"(?i)^\s*(loop|opt|alt|par|critical|break|rect)\b\s*(.*)$")
_FRAGMENT_DIVIDER_RE = re.compile(r"(?i)^\s*(else|and|option)\b\s*(.*)$")
_RECT_COLOR_RE = re.compile(r"(?i)^\s*rgba?\([^)]*\)\s*")
_FRAGMENT_END_RE = re.compile(r"(?i)^\s*end\s*$")
_NOTE_RE = re.compile(r'(?i)^\s*note\s+(right of|left of|over)\s+([^:]+?)\s*:\s*(.*)$')


class ParseError(Exception):
    pass


class FragmentType(Enum):
    LOOP = "loop"
    OPT = "opt"
    ALT = "alt"
    PAR = "par"
    CRITICAL = "critical"
    BREAK = "break"
    RECT = "rect"


_FRAGMENT_KEYWORDS = {t.value: t for t in FragmentType}
_DIVIDER_KEYWORDS = {
    "else": FragmentType.ALT, "and": FragmentType.PAR, "option": FragmentType.CRITICAL,
}


class NotePlacement(Enum):
    OVER = auto()
    LEFT_OF = auto()
    RIGHT_OF = auto()


class ArrowType(Enum):
    SOLID_ARROW = "->>"  # solid line with an arrowhead
    DOTTED_ARROW = "-->>"  # dotted line with an arrowhead
    SOLID_OPEN = "->"  # solid line, no arrowhead
    DOTTED_OPEN = "-->"  # dotted line, no arrowhead
    SOLID_CROSS = "-x"  # solid line, cross head (lost/failed message)
    DOTTED_CROSS = "--x"  # dotted line, cross head
    SOLID_POINT = "-)"  # solid line, open point head (async message)
    DOTTED_POINT = "--)"  # dotted line, open point head
    BIDIRECTIONAL_SOLID = "<<->>"  # solid line, arrowheads both ends
    BIDIRECTIONAL_DOTTED = "<<-->>"  # dotted line, arrowheads both ends

    @property
    def is_dotted(self) -> bool:
        return self in (
            ArrowType.DOTTED_ARROW, ArrowType.DOTTED_OPEN,
            ArrowType.DOTTED_CROSS, ArrowType.DOTTED_POINT,
            ArrowType.BIDIRECTIONAL_DOTTED,
        )

    @property
    def is_bidirectional(self) -> bool:
        return self in (ArrowType.BIDIRECTIONAL_SOLID, ArrowType.BIDIRECTIONAL_DOTTED)

    def head(self, chars, rightward: bool) -> tuple[str, bool]:
        """The glyph drawn where the arrow meets the target lifeline, and False
        for the open forms (-> and -->), which are drawn as a plain line
        touching the lifeline. `rightward` selects the direction the head
        points."""
        if self in (ArrowType.SOLID_ARROW, ArrowType.DOTTED_ARROW,
                    ArrowType.BIDIRECTIONAL_SOLID, ArrowType.BIDIRECTIONAL_DOTTED):
            return (chars.arrow_right, True) if rightward else (chars.arrow_left, True)
        if self in (ArrowType.SOLID_CROSS, ArrowType.DOTTED_CROSS):
            return chars.cross_head, True
        if self in (ArrowType.SOLID_POINT, ArrowType.DOTTED_POINT):
            return (chars.point_right, True) if rightward else (chars.point_left, True)
        return "", False


_ARROW_SYNTAX = {a.value: a for a in ArrowType}


@dataclass
class Participant:
    id: str
    label: str
    index: int
    is_actor: bool = False


@dataclass
class Message:
    from_: Participant
    to: Participant
    label: str
    arrow_type: ArrowType
    central_from: bool = False
    central_to: bool = False
    number: int = 0  # message number when autonumber is enabled (0 means no number)


@dataclass
class Fragment:
    type: FragmentType
    label: str


@dataclass
class Note:
    placement: NotePlacement
    participants: list[Participant]
    text: str


class EventKind(Enum):
    MESSAGE = auto()
    FRAGMENT_START = auto()
    FRAGMENT_DIVIDER = auto()
    FRAGMENT_END = auto()
    NOTE = auto()


@dataclass
class Event:
    kind: EventKind
    message: Message | None = None
    fragment: Fragment | None = None
    note: Note | None = None


@dataclass
class SequenceDiagram:
    participants: list[Participant] = field(default_factory=list)
    # Messages is the flat list of every message arrow, in source order and
    # independent of any fragment nesting.
    messages: list[Message] = field(default_factory=list)
    # Events is the ordered body of the diagram used for rendering: each entry
    # is either a message or a fragment boundary. Walking events reproduces the
    # original source order, including where loop/opt blocks open and close.
    events: list[Event] = field(default_factory=list)
    autonumber: bool = False

    def get_participant(self, id_: str, participants: dict[str, Participant]) -> Participant:
        p = participants.get(id_)
        if p is not None:
            return p
        p = Participant(id=id_, label=id_, index=len(self.participants))
        self.participants.append(p)
        participants[id_] = p
        return p


def _has_sequence_keyword(line: str) -> bool:
    """Whether `line` is the sequenceDiagram declaration, case-insensitively.
    The keyword must stand as a whole token -- followed by whitespace or end of
    line -- so a node id like "sequenceDiagramFoo" in a flowchart isn't
    misrouted here."""
    lower = line.strip().lower()
    kw = SEQUENCE_DIAGRAM_KEYWORD.lower()
    if not lower.startswith(kw):
        return False
    rest = lower[len(kw):]
    return rest == "" or rest[0] in (" ", "\t")


def sniff(text: str) -> bool:
    """Whether `text` opens with the sequenceDiagram keyword (ignoring blank
    lines and %% comments)."""
    for line in text.split("\n"):
        trimmed = line.strip()
        if trimmed == "" or trimmed.startswith("%%"):
            continue
        return _has_sequence_keyword(trimmed)
    return False


def parse(text: str) -> SequenceDiagram:
    text = text.strip()
    if not text:
        raise ParseError("empty input")

    raw_lines = split_lines(text)
    lines = remove_comments(raw_lines)
    if not lines:
        raise ParseError("no content found")

    if not _has_sequence_keyword(lines[0].strip()):
        raise ParseError(f'expected "{SEQUENCE_DIAGRAM_KEYWORD}" keyword')
    lines = lines[1:]

    sd = SequenceDiagram()
    participant_map: dict[str, Participant] = {}
    # open_fragments is a stack of the fragment types currently open, so we can
    # reject an "end"/"else" with no matching opener, validate that "else" only
    # appears inside an "alt", and detect an opener with no matching "end".
    open_fragments: list[FragmentType] = []

    for i, line in enumerate(lines):
        trimmed = line.strip()
        if trimmed == "":
            continue

        if _AUTONUMBER_RE.match(trimmed):
            sd.autonumber = True
            continue

        # Notes carry no arrow, so they never collide with messages; a
        # placement keyword is required, so a participant named "Note" (e.g.
        # "Note->>B: hi") still parses as a message further down.
        m = _NOTE_RE.match(trimmed)
        if m is not None:
            placement = {
                "left of": NotePlacement.LEFT_OF,
                "right of": NotePlacement.RIGHT_OF,
            }.get(m.group(1).lower(), NotePlacement.OVER)
            parts: list[Participant] = []
            for id_ in m.group(2).split(","):
                id_ = id_.strip().strip('"')
                if id_:
                    parts.append(sd.get_participant(id_, participant_map))
            if not parts:
                raise ParseError(f"line {i + 2}: note without a participant")
            # Mermaid allows an optional wrap:/nowrap: prefix on note text;
            # wrapping is irrelevant for single-line ASCII, so just strip it.
            text_ = m.group(3).strip()
            for prefix in ("nowrap:", "wrap:"):
                if text_.lower().startswith(prefix):
                    text_ = text_[len(prefix):].strip()
                    break
            sd.events.append(Event(
                kind=EventKind.NOTE,
                note=Note(placement=placement, participants=parts, text=text_),
            ))
            continue

        matched, err = _parse_participant(sd, trimmed, participant_map)
        if err:
            raise ParseError(f"line {i + 2}: {err}")
        if matched:
            continue

        # Messages are checked before fragment keywords so a participant named
        # "loop"/"opt"/"end" (e.g. "loop->>B: hi") is still read as a message --
        # only bare openers like "loop retry" fall through to the checks below.
        if _parse_message(sd, trimmed, participant_map):
            continue

        # A fragment opener (loop/opt/alt/par/critical/break/rect) starts a block.
        match = _FRAGMENT_START_RE.match(trimmed)
        if match is not None:
            f_type = _FRAGMENT_KEYWORDS[match.group(1).lower()]
            label = match.group(2).strip()
            # rect's argument is a fill colour we can't render in ASCII; drop it
            # so the frame is drawn plain.
            if f_type is FragmentType.RECT:
                label = _RECT_COLOR_RE.sub("", label).strip()
            sd.events.append(Event(
                kind=EventKind.FRAGMENT_START, fragment=Fragment(type=f_type, label=label),
            ))
            open_fragments.append(f_type)
            continue

        # A section divider: "else" (alt), "and" (par), "option" (critical). It
        # must sit directly inside the matching fragment type.
        match = _FRAGMENT_DIVIDER_RE.match(trimmed)
        if match is not None:
            want = _DIVIDER_KEYWORDS[match.group(1).lower()]
            if not open_fragments or open_fragments[-1] is not want:
                raise ParseError(f'line {i + 2}: "{trimmed}" outside a matching {want.value} block')
            sd.events.append(Event(
                kind=EventKind.FRAGMENT_DIVIDER,
                fragment=Fragment(type=want, label=match.group(2).strip()),
            ))
            continue

        # "end" closes the most recently opened fragment.
        if _FRAGMENT_END_RE.match(trimmed):
            if not open_fragments:
                raise ParseError(f'line {i + 2}: "{trimmed}" without a matching fragment opener')
            sd.events.append(Event(kind=EventKind.FRAGMENT_END))
            open_fragments.pop()
            continue

        raise ParseError(f'line {i + 2}: invalid syntax: "{trimmed}"')

    if open_fragments:
        raise ParseError(f'unclosed fragment: missing {len(open_fragments)} "end"')

    if not sd.participants:
        raise ParseError("no participants found")

    return sd


def _parse_participant(
    sd: SequenceDiagram, line: str, participants: dict[str, Participant]
) -> tuple[bool, str | None]:
    match = _PARTICIPANT_RE.match(line)
    if match is None:
        return False, None

    id_ = match.group(2) or ""
    if match.group(1):
        id_ = match.group(1)
    label = match.group(3) or ""
    if not label:
        label = id_
    label = label.strip('"')

    if id_ in participants:
        return True, f'duplicate participant "{id_}"'

    is_actor = bool(_ACTOR_KEYWORD_RE.match(line))
    p = Participant(id=id_, label=label, index=len(sd.participants), is_actor=is_actor)
    sd.participants.append(p)
    participants[id_] = p
    return True, None


def _parse_message(sd: SequenceDiagram, line: str, participants: dict[str, Participant]) -> bool:
    match = _MESSAGE_RE.match(line)
    if match is None:
        return False

    from_id = match.group(2) or match.group(1) or ""
    central_from = bool(match.group(3))
    arrow = match.group(4)
    central_to = bool(match.group(5))
    to_id = match.group(7) or match.group(6) or ""
    label = match.group(8).strip()

    from_ = sd.get_participant(from_id, participants)
    to = sd.get_participant(to_id, participants)
    a_type = _ARROW_SYNTAX[arrow]

    msg_number = 0
    if sd.autonumber:
        msg_number = len(sd.messages) + 1

    msg = Message(
        from_=from_, to=to, label=label, arrow_type=a_type,
        central_from=central_from, central_to=central_to, number=msg_number,
    )
    sd.messages.append(msg)
    sd.events.append(Event(kind=EventKind.MESSAGE, message=msg))
    return True
