"""Entity-relationship diagram parser, ported from pkg/er/parser.go."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto

from viewmd.mermaid.textutil import split_lines, strip_front_matter

ER_DIAGRAM_KEYWORD = "erDiagram"

# --- regexes, transcribed 1:1 from parser.go ---

# lineOpRegex matches the relationship line operator (a 2-char run of - and .
# -- entity names use single dashes, so this uniquely marks the connector).
_LINE_OP_RE = re.compile(r"[-.]{2}")

# directionRegex matches the optional "direction TB|LR|..." layout directive.
_DIRECTION_RE = re.compile(r"(?i)^\s*direction\s+\S+\s*$")

# styleLineRegex matches visual-styling lines that carry no ASCII meaning;
# they're skipped so a stray one doesn't fail a diagram. Checked after the
# entity-header form so an entity that happens to be named `class` still works.
_STYLE_LINE_RE = re.compile(r"(?i)^\s*(classDef|class|style)\b")

# accLineRegex matches accessibility metadata: `accTitle: ...`, `accDescr: ...`,
# or the multi-line `accDescr {` block form (whose body is skipped too).
_ACC_LINE_RE = re.compile(r"(?i)^\s*(accTitle|accDescr)\s*[:{]")

# entityHeaderRegex matches the opening of an attribute block, with an
# optional alias: `NAME {`, `NAME alias {`, `NAME[Alias] {`, or
# `NAME["Alias Label"] {`.
_ENTITY_HEADER_RE = re.compile(
    r'^\s*(?:"([^"]+)"|([^\s{}["]+))(?:\s*\[\s*"?([^"\]]+?)"?\s*\]|\s+(\S+))?\s*\{\s*$'
)

# loneEntityRegex matches an entity declared on its own (no block/relation),
# with an optional alias: `NAME`, `NAME alias`, `NAME[Alias]`, or
# `NAME["Alias Label"]`.
_LONE_ENTITY_RE = re.compile(
    r'^\s*(?:"([^"]+)"|([^\s{}:|"\[]+))(?:\s*\[\s*"?([^"\]]+?)"?\s*\]|\s+(\S+))?\s*$'
)

# attrKeyRegex matches a PK/FK/UK key token (possibly comma-separated).
_ATTR_KEY_RE = re.compile(r"^(?:PK|FK|UK)(?:\s*,\s*(?:PK|FK|UK))*$")

# emptyBlockRegex matches a one-line empty attribute block suffix: `NAME {}`.
_EMPTY_BLOCK_RE = re.compile(r"\s*\{\s*\}\s*$")

# classShorthandRegex matches a `:::class[,class...]` styling decoration on an
# entity; like classDef/class lines it carries no ASCII meaning.
_CLASS_SHORTHAND_RE = re.compile(r":::[\w,-]+")

# subgraphRegex matches the opening of an er subgraph block (an unreleased
# upstream feature this renderer rejects rather than mis-draws).
_SUBGRAPH_RE = re.compile(r"^subgraph\b")


class ParseError(Exception):
    pass


class Cardinality(Enum):
    ONLY_ONE = auto()  # ||   exactly one
    ZERO_OR_ONE = auto()  # |o / o|   zero or one
    ZERO_OR_MORE = auto()  # }o / o{   zero or more
    ONE_OR_MORE = auto()  # }| / |{   one or more


# cardAny maps every cardinality form mermaid accepts -- crow's-foot tokens
# (either side), numeric shorthands, and word phrases -- to a Cardinality.
_CARD_ANY: dict[str, Cardinality] = {
    # crow's-foot tokens (accepted on either side)
    "||": Cardinality.ONLY_ONE,
    "|o": Cardinality.ZERO_OR_ONE, "o|": Cardinality.ZERO_OR_ONE,
    "}o": Cardinality.ZERO_OR_MORE, "o{": Cardinality.ZERO_OR_MORE,
    "}|": Cardinality.ONE_OR_MORE, "|{": Cardinality.ONE_OR_MORE,
    # numeric / word shorthands
    "1": Cardinality.ONLY_ONE, "only one": Cardinality.ONLY_ONE, "one": Cardinality.ONLY_ONE,
    "zero or one": Cardinality.ZERO_OR_ONE, "one or zero": Cardinality.ZERO_OR_ONE,
    "0+": Cardinality.ZERO_OR_MORE, "zero or more": Cardinality.ZERO_OR_MORE,
    "zero or many": Cardinality.ZERO_OR_MORE,
    "many": Cardinality.ZERO_OR_MORE, "many(0)": Cardinality.ZERO_OR_MORE,
    "1+": Cardinality.ONE_OR_MORE, "one or more": Cardinality.ONE_OR_MORE,
    "one or many": Cardinality.ONE_OR_MORE, "many(1)": Cardinality.ONE_OR_MORE,
}


@dataclass
class Attribute:
    type: str
    name: str
    keys: list[str] = field(default_factory=list)  # PK, FK, UK
    comment: str = ""


@dataclass
class Entity:
    """A named box with an optional list of attributes. name is the id used in
    relationships; display is the label shown in the box (an alias if one was
    given, otherwise the name)."""

    name: str
    display: str
    attributes: list[Attribute] = field(default_factory=list)


@dataclass
class Relationship:
    left: str
    right: str
    left_card: Cardinality
    right_card: Cardinality
    identifying: bool  # true for a solid (--) line, false for dashed (..)
    label: str


@dataclass
class ErDiagram:
    """A parsed entity-relationship diagram. Entities are kept in first-seen
    order; a relationship referencing an undeclared entity auto-creates it."""

    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    _by_name: dict[str, Entity] = field(default_factory=dict, repr=False)

    def entity(self, name: str) -> Entity:
        e = self._by_name.get(name)
        if e is not None:
            return e
        e = Entity(name=name, display=name)
        self._by_name[name] = e
        self.entities.append(e)
        return e


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line (after an optional YAML
    front-matter block) declares an erDiagram (case-insensitive, whole
    token)."""
    for line in strip_front_matter(text).split("\n"):
        t = line.strip()
        if t == "" or t.startswith("%%"):
            continue
        low = t.lower()
        kw = ER_DIAGRAM_KEYWORD.lower()
        return low == kw or low.startswith(kw + " ")
    return False


def parse(text: str) -> ErDiagram:
    if not sniff(text):
        raise ParseError(f'expected "{ER_DIAGRAM_KEYWORD}" keyword')
    # Comments are stripped in place (not filtered out as whole lines) so error
    # messages report the caller's real line numbers.
    lines = split_lines(strip_front_matter(text).strip())
    lines = [_strip_comment(line) for line in lines]

    d = ErDiagram()

    seen_keyword = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if line == "":
            i += 1
            continue
        if not seen_keyword:  # the erDiagram keyword line itself (verified above)
            seen_keyword = True
            i += 1
            continue

        # Accessibility / layout-direction lines carry no ASCII meaning here --
        # skip them (including an `accDescr { ... }` block) rather than failing.
        if _ACC_LINE_RE.match(line):
            if line.endswith("{"):
                i += 1
                while i < n and "}" not in lines[i]:
                    i += 1
            i += 1
            continue
        if _DIRECTION_RE.match(line):
            i += 1
            continue

        # er subgraphs (unreleased upstream) would otherwise misparse into
        # bogus entity boxes -- reject them loudly instead.
        if _SUBGRAPH_RE.match(line) or line == "end":
            raise ParseError(f"line {i + 1}: er subgraphs are not supported")

        # `:::class` styling decorations carry no ASCII meaning; strip them
        # (outside quoted strings) so the decorated statement parses normally.
        if ":::" in line:
            line = _strip_class_shorthand(line)

        # A one-line empty attribute block (`NAME {}`) is just an entity
        # declaration; strip the block and let the lone-entity form match.
        if _EMPTY_BLOCK_RE.search(line):
            line = _EMPTY_BLOCK_RE.sub("", line).strip()

        # Entity attribute block: NAME { ... } (with optional alias). Checked
        # before the style-line skip so entities named e.g. `class` still work.
        m = _ENTITY_HEADER_RE.match(line)
        if m is not None:
            name = _first_non_empty(m.group(1), m.group(2))
            e = d.entity(name)
            alias = _first_non_empty(m.group(3), m.group(4))
            if alias:
                e.display = alias
            try:
                attrs, next_i = _parse_attribute_block(lines, i + 1)
            except ParseError as exc:
                raise ParseError(f'entity "{name}": {exc}') from exc
            e.attributes.extend(attrs)  # multiple blocks accumulate
            i = next_i + 1  # index of the closing "}"
            continue

        # Relationship (any cardinality form: crow's-foot, numeric, or words).
        # Checked before the style-line skip -- a relationship always carries a
        # connector and a colon, which no styling directive does, so an entity
        # named `class` keeps its relationships.
        if _parse_relationship(d, line):
            i += 1
            continue

        # Visual styling directives (classDef/class/style) have no ASCII meaning.
        if _STYLE_LINE_RE.match(line):
            i += 1
            continue

        # A bare entity name (with optional alias) declares an entity.
        m = _LONE_ENTITY_RE.match(line)
        if m is not None:
            e = d.entity(_first_non_empty(m.group(1), m.group(2)))
            alias = _first_non_empty(m.group(3), m.group(4))
            if alias:
                e.display = alias
            i += 1
            continue

        raise ParseError(f'line {i + 1}: invalid syntax: "{line}"')

    # A statement-less erDiagram is valid mermaid; it renders as empty output.
    return d


def _parse_attribute_block(lines: list[str], start: int) -> tuple[list[Attribute], int]:
    """Read attribute rows until the closing "}", returning the attributes and
    the index of the closing-brace line."""
    attrs: list[Attribute] = []
    for i in range(start, len(lines)):
        line = lines[i].strip()
        if line == "" or line.startswith("//"):
            continue  # blank or a // note line (some diagrams use these)
        # Mermaid allows the closing brace on the last attribute's line
        # ("string title}"), so a trailing "}" closes the block after the
        # attribute (if any) on that line is parsed. Quoted comments never
        # end in a bare "}" -- the quote is the last character.
        closes = line.endswith("}")
        if closes:
            line = line[:-1].strip()
        if line != "":
            try:
                attrs.append(_parse_attribute(line))
            except ParseError as exc:
                raise ParseError(f"line {i + 1}: {exc}") from exc
        if closes:
            return attrs, i
    raise ParseError("unclosed attribute block (missing '}')")


def _parse_attribute(line: str) -> Attribute:
    """Parse "type name [keys] [\"comment\"]"."""
    # Pull a trailing quoted comment off first. Tolerate an unclosed quote
    # (some hand-written diagrams forget the closing ") by taking the rest.
    comment = ""
    idx = line.find('"')
    if idx != -1:
        end = line.rfind('"')
        if end > idx:
            comment = line[idx + 1:end]
        else:
            comment = line[idx + 1:]
        line = line[:idx].strip()
    fields_ = _split_attr_tokens(line)
    if len(fields_) < 2:
        raise ParseError(f'attribute needs a type and name: "{line}"')
    # Backtick escaping (`geo.accuracy`) exists only to smuggle special
    # characters past mermaid's lexer; the backticks themselves never render.
    attr = Attribute(type=fields_[0].strip("`"), name=fields_[1].strip("`"), comment=comment)
    rest = " ".join(fields_[2:]).strip()
    if rest:
        if not _ATTR_KEY_RE.match(rest):
            raise ParseError(f'unexpected attribute tokens "{rest}"')
        attr.keys = [k.strip() for k in rest.split(",")]
    return attr


def _strip_class_shorthand(line: str) -> str:
    """Remove `:::class[,class...]` decorations from the parts of a line
    outside double-quoted strings."""
    parts = line.split('"')
    for i in range(0, len(parts), 2):  # even indices are outside quotes
        parts[i] = _CLASS_SHORTHAND_RE.sub("", parts[i])
    return '"'.join(parts)


def _strip_comment(line: str) -> str:
    """Drop a %% comment (whole-line or trailing) from a line. %% inside a
    quoted string (a label or attribute comment) is kept, matching mermaid's
    lexer, which tokenizes strings before comments."""
    in_quote = False
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == '"':
            in_quote = not in_quote
        elif not in_quote and c == "%" and i + 1 < n and line[i + 1] == "%":
            return line[:i].rstrip(" \t")
        i += 1
    return line


def _first_non_empty(a: str | None, b: str | None) -> str:
    if a:
        return a
    return b or ""


def _parse_relationship(d: ErDiagram, line: str) -> bool:
    """Parse any relationship form and append it to d, returning True if the
    line was a relationship. Cardinality on each side may be a crow's-foot
    token (||, o{, ...), a numeric shorthand (1, 0+, 1+), or a word phrase
    (only one, one or more, ...); the connector is -- / .. / -. / .- or the
    word operator "to" / "optionally to"."""
    colon = line.find(":")
    if colon < 0:
        return False
    main = line[:colon].strip()
    # Collapse label whitespace like mermaid's SVG text rendering does; a
    # whitespace-only label would otherwise punch blank holes in its line.
    label = " ".join(line[colon + 1:].strip().strip('"').split())

    m = _LINE_OP_RE.search(main)
    if m is not None:
        left = main[:m.start()].strip()
        right = main[m.end():].strip()
        identifying = main[m.start():m.end()] == "--"
    else:
        idx, w = _find_word_op(main)
        if idx < 0:
            return False
        left = main[:idx].strip()
        right = main[idx + len(w):].strip()
        identifying = w == " to "

    e1, lcard = _split_entity_card(left, True)
    e2, rcard = _split_entity_card(right, False)
    lc = _CARD_ANY.get(lcard.lower())
    rc = _CARD_ANY.get(rcard.lower())
    if not e1 or not e2 or lc is None or rc is None:
        return False
    d.entity(e1)
    d.entity(e2)
    d.relationships.append(Relationship(
        left=e1, right=e2, left_card=lc, right_card=rc,
        identifying=identifying, label=label,
    ))
    return True


def _find_word_op(s: str) -> tuple[int, str]:
    """Locate the " to " / " optionally to " word connector."""
    for w in (" optionally to ", " to "):
        i = s.find(w)
        if i >= 0:
            return i, w
    return -1, ""


def _split_entity_card(part: str, entity_first: bool) -> tuple[str, str]:
    """Split "ENTITY <card>" (entity_first) or "<card> ENTITY" into the entity
    id and the cardinality text. Quoted names may contain spaces."""
    part = part.strip()
    if entity_first:
        if part.startswith('"'):
            end = part[1:].find('"')
            if end >= 0:
                return part[1:end + 1], part[end + 2:].strip()
        toks = part.split()
        if not toks:
            return "", ""
        return toks[0].strip('"'), " ".join(toks[1:])
    if part.endswith('"'):
        start = part[:-1].rfind('"')
        if start >= 0:
            return part[start + 1:-1], part[:start].strip()
    toks = part.split()
    if not toks:
        return "", ""
    return toks[-1].strip('"'), " ".join(toks[:-1])


def _split_attr_tokens(s: str) -> list[str]:
    """Split on whitespace but keep parenthesised and backtick-escaped groups
    intact, so a type like "decimal(10, 2)" or a name like `two words` stays a
    single token."""
    toks: list[str] = []
    cur: list[str] = []
    depth = 0
    in_tick = False

    def flush() -> None:
        if cur:
            toks.append("".join(cur))
            cur.clear()

    for r in s:
        if r == "`":
            in_tick = not in_tick
            cur.append(r)
        elif r == "(" and not in_tick:
            depth += 1
            cur.append(r)
        elif r == ")" and not in_tick:
            if depth > 0:
                depth -= 1
            cur.append(r)
        elif r in (" ", "\t") and depth == 0 and not in_tick:
            flush()
        else:
            cur.append(r)
    flush()
    return toks
