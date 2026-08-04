"""Sequence-diagram ASCII/Unicode renderer, ported from pkg/sequence/renderer.go."""

from __future__ import annotations

import random
from dataclasses import dataclass

from wcwidth import wcswidth

from viewmd.mermaid.sequence.charset import ASCII, UNICODE, BoxChars
from viewmd.mermaid.sequence.parser import (
    Event,
    EventKind,
    Fragment,
    Message,
    Note,
    NotePlacement,
    Participant,
    SequenceDiagram,
)

DEFAULT_SELF_MESSAGE_WIDTH = 4
DEFAULT_MESSAGE_SPACING = 1
DEFAULT_PARTICIPANT_SPACING = 5
BOX_PADDING_LEFT_RIGHT = 2
MIN_BOX_WIDTH = 3
BOX_BORDER_WIDTH = 2
LABEL_LEFT_MARGIN = 2
LABEL_BUFFER_SPACE = 10
FRAME_INDENT = 2  # columns reserved per nested fragment level
FRAME_LABEL_INSET = 2  # columns from the left corner to the "[label]" tab

# Three-line stick figures drawn above an `actor` participant's label
# (VIEWMD-0020), each row exactly 3 characters wide: (head, arms/torso, legs).
# One is picked at random per actor; with more than one actor in a diagram
# they're drawn round-robin from a shuffled copy of this list so adjacent
# actors don't repeat needlessly before every figure has been used once.
ACTOR_FIGURES: list[tuple[str, str, str]] = [
    (" O ", "\\|/", "/ \\"),
    (" o ", "/.7", "/ \\"),
    (" o ", "<|>", "/ \\"),
    (" o ", "(|)", "/ \\"),
    ("\\o/", " | ", "/ \\"),
]


def _width(s: str) -> int:
    w = wcswidth(s)
    return w if w >= 0 else len(s)


@dataclass
class DiagramLayout:
    participant_widths: list[int]
    participant_centers: list[int]
    total_width: int
    message_spacing: int
    self_message_width: int


def calculate_layout(
    sd: SequenceDiagram, *,
    participant_spacing: int = DEFAULT_PARTICIPANT_SPACING,
    message_spacing: int = DEFAULT_MESSAGE_SPACING,
    self_message_width: int = DEFAULT_SELF_MESSAGE_WIDTH,
) -> DiagramLayout:
    if participant_spacing <= 0:
        participant_spacing = DEFAULT_PARTICIPANT_SPACING

    widths = []
    for p in sd.participants:
        w = _width(p.label) + BOX_PADDING_LEFT_RIGHT
        widths.append(max(w, MIN_BOX_WIDTH))

    centers = [0] * len(sd.participants)
    current_x = 0
    for i in range(len(sd.participants)):
        box_width = widths[i] + BOX_BORDER_WIDTH
        if i == 0:
            centers[i] = box_width // 2
            current_x = box_width
        else:
            current_x += participant_spacing
            centers[i] = current_x + box_width // 2
            current_x += box_width

    last = len(sd.participants) - 1
    total_width = centers[last] + (widths[last] + BOX_BORDER_WIDTH) // 2

    if message_spacing <= 0:
        message_spacing = DEFAULT_MESSAGE_SPACING
    if self_message_width <= 0:
        self_message_width = DEFAULT_SELF_MESSAGE_WIDTH

    return DiagramLayout(
        participant_widths=widths, participant_centers=centers, total_width=total_width,
        message_spacing=message_spacing, self_message_width=self_message_width,
    )


def render(
    sd: SequenceDiagram, *,
    use_ascii: bool = False,
    participant_spacing: int = DEFAULT_PARTICIPANT_SPACING,
    message_spacing: int = DEFAULT_MESSAGE_SPACING,
    self_message_width: int = DEFAULT_SELF_MESSAGE_WIDTH,
    rng: random.Random | None = None,
) -> str:
    if not sd.participants:
        raise ValueError("no participants")

    chars = ASCII if use_ascii else UNICODE
    layout = calculate_layout(
        sd, participant_spacing=participant_spacing,
        message_spacing=message_spacing, self_message_width=self_message_width,
    )

    # Fall back to a message-only body for diagrams built without an event
    # stream.
    events = sd.events
    if not events:
        events = [Event(kind=EventKind.MESSAGE, message=m) for m in sd.messages]

    # Nested fragment frames stack their left borders in a gutter to the left of
    # the first participant. A single (unnested) fragment already fits with its
    # border at column 0, so only levels beyond the first need reserved columns;
    # shift the whole diagram right so the borders never overlap the lifelines.
    gutter = (_fragment_depth(events) - 1) * FRAME_INDENT
    if gutter > 0:
        _shift_layout_right(layout, gutter)

    # A "left of" note on the leftmost participant, or a wide "over" note,
    # extends past column 0. Reserve an additional left gutter so no note box is
    # clamped on top of lifelines it shouldn't cover.
    gutter = _note_left_gutter(events, layout)
    if gutter > 0:
        _shift_layout_right(layout, gutter)

    lines: list[str] = []

    has_actor = any(p.is_actor for p in sd.participants)

    def _box_width(i: int) -> int:
        return layout.participant_widths[i] + BOX_BORDER_WIDTH

    # Assign each actor a stick figure. Drawn round-robin from a shuffled copy
    # of ACTOR_FIGURES so multiple actors in one diagram get different figures
    # before any repeat (falls back to repeating once the pool is exhausted).
    figure_for_index: dict[int, tuple[str, str, str]] = {}
    if has_actor:
        rng = rng or random.Random()  # noqa: S311 -- cosmetic glyph choice, not security-sensitive
        pool = ACTOR_FIGURES.copy()
        rng.shuffle(pool)
        actor_indices = [i for i, p in enumerate(sd.participants) if p.is_actor]
        for n, idx in enumerate(actor_indices):
            figure_for_index[idx] = pool[n % len(pool)]

    def _centered_3(i: int, glyph: str) -> str:
        """Place a 3-char glyph centered at this participant's box center."""
        w = _box_width(i)
        center = w // 2
        return " " * (center - 1) + glyph + " " * (w - center - 2)

    # An `actor` participant draws a 3-line stick figure (head, arms/torso,
    # legs) above its label instead of a box top. The head/arms rows are extra
    # header rows a plain-box diagram doesn't have -- only reserve them when at
    # least one actor is present, so a diagram with no actors renders
    # byte-for-byte as before (VIEWMD-0020 requirement 4). The legs row merges
    # into the existing top-border row below: an actor draws its legs there, a
    # plain participant its usual box top, keeping every participant's header
    # the same total height within one diagram.
    if has_actor:
        for row in (0, 1):
            def _figure_line(i: int, row: int = row) -> str:
                if i not in figure_for_index:
                    return " " * _box_width(i)
                return _centered_3(i, figure_for_index[i][row])

            lines.append(_build_line(sd.participants, layout, _figure_line))

    def _top_line(i: int) -> str:
        if i in figure_for_index:
            return _centered_3(i, figure_for_index[i][2])  # legs
        return chars.top_left + chars.horizontal * layout.participant_widths[i] + chars.top_right

    lines.append(_build_line(sd.participants, layout, _top_line))

    def _label_line(i: int) -> str:
        label = sd.participants[i].label
        label_len = _width(label)
        if i in figure_for_index:
            w = _box_width(i)
            pad = (w - label_len) // 2
            return " " * pad + label + " " * (w - pad - label_len)
        w = layout.participant_widths[i]
        pad = (w - label_len) // 2
        return chars.vertical + " " * pad + label + " " * (w - pad - label_len) + chars.vertical

    def _border_line(i: int) -> str:
        w = layout.participant_widths[i]
        if i in figure_for_index:
            box_width = _box_width(i)
            center = box_width // 2
            return " " * center + chars.vertical + " " * (box_width - center - 1)
        return (chars.bottom_left + chars.horizontal * (w // 2) + chars.tee_down
                + chars.horizontal * (w - w // 2 - 1) + chars.bottom_right)

    lines.append(_build_line(sd.participants, layout, _label_line))
    lines.append(_build_line(sd.participants, layout, _border_line))

    lines.extend(_render_events(events, layout, chars))

    lines.append(_build_lifeline(layout, chars))
    return "\n".join(lines) + "\n"


def _render_events(events: list[Event], layout: DiagramLayout, chars: BoxChars) -> list[str]:
    """Paint the ordered body of the diagram -- messages and fragment frames --
    into text lines. Recurses into each loop/opt block, so nested fragments
    render correctly."""
    lines: list[str] = []
    i = 0
    while i < len(events):
        ev = events[i]
        if ev.kind is EventKind.FRAGMENT_START:
            end = _matching_fragment_end(events, i)
            lines.extend(_wrap_fragment(ev.fragment, events[i + 1:end], layout, chars))
            i = end + 1
            continue

        # EventFragmentEnd is consumed by matching_fragment_end, and top-level
        # EventFragmentDivider is consumed by wrap_fragment's section split, so
        # neither should reach here -- skip defensively.
        if ev.kind in (EventKind.FRAGMENT_END, EventKind.FRAGMENT_DIVIDER):
            i += 1
            continue

        if ev.kind is EventKind.NOTE:
            for _ in range(layout.message_spacing):
                lines.append(_build_lifeline(layout, chars))
            lines.extend(_render_note(ev.note, layout, chars))
            i += 1
            continue

        # EventKind.MESSAGE.
        msg = ev.message
        for _ in range(layout.message_spacing):
            lines.append(_build_lifeline(layout, chars))
        if msg.from_ is msg.to:
            lines.extend(_render_self_message(msg, layout, chars))
        else:
            lines.extend(_render_message(msg, layout, chars))
        i += 1
    return lines


def _fragment_depth(events: list[Event]) -> int:
    """The maximum fragment nesting depth within events (0 if there are none)."""
    max_depth = cur = 0
    for ev in events:
        if ev.kind is EventKind.FRAGMENT_START:
            cur += 1
            max_depth = max(max_depth, cur)
        elif ev.kind is EventKind.FRAGMENT_END:
            cur -= 1
    return max_depth


def _matching_fragment_end(events: list[Event], start: int) -> int:
    """The index of the EventFragmentEnd that closes the fragment opened at
    `start`, accounting for nested fragments."""
    depth = 0
    for i in range(start, len(events)):
        if events[i].kind is EventKind.FRAGMENT_START:
            depth += 1
        elif events[i].kind is EventKind.FRAGMENT_END:
            depth -= 1
            if depth == 0:
                return i
    return len(events)  # unreachable: the parser guarantees balanced fragments


def _shift_layout_right(layout: DiagramLayout, n: int) -> None:
    """Move every participant (and the total width) right by n columns,
    reserving a left gutter for content that extends past column 0."""
    layout.participant_centers = [c + n for c in layout.participant_centers]
    layout.total_width += n


def _note_left_gutter(events: list[Event], layout: DiagramLayout) -> int:
    """How many columns the diagram must shift right so that every note box --
    and the border of each fragment frame enclosing it -- fits at or right of
    column 0."""
    gutter = depth = 0
    for ev in events:
        if ev.kind is EventKind.FRAGMENT_START:
            depth += 1
        elif ev.kind is EventKind.FRAGMENT_END:
            depth -= 1
        elif ev.kind is EventKind.NOTE:
            left, _ = _note_box_columns(ev.note, layout)
            # A top-level note only needs its own box at column 0. A note d
            # frames deep also needs the outermost enclosing border, which sits
            # 1+(d-1)*FRAME_INDENT columns to its left (see wrap_fragment's
            # stagger).
            extra = 1 + (depth - 1) * FRAME_INDENT if depth > 0 else 0
            need = -left + extra
            if need > gutter:
                gutter = need
    return gutter


def _note_text(note: Note) -> str:
    """A note's display text with mermaid line breaks collapsed to spaces (ASCII
    output is single-line)."""
    text = note.text
    for br in ("<br/>", "<br />", "<br>"):
        text = text.replace(br, " ")
    return text


def _note_box_columns(note: Note, layout: DiagramLayout) -> tuple[int, int]:
    """The [left, right] columns a note's box occupies. For `over`, the box
    always spans its participants (first..last) and widens symmetrically to fit
    the text; for left/right of it sits beside the lifeline. `left` may be
    negative when a left-of box extends past column 0 -- render() reserves a
    gutter so that never happens at draw time."""
    box_w = len(_note_text(note)) + 4  # "│ text │"
    centers = layout.participant_centers
    first = centers[note.participants[0].index]
    last = centers[note.participants[-1].index]

    if note.placement is NotePlacement.RIGHT_OF:
        left = first + 2
        return left, left + box_w - 1
    if note.placement is NotePlacement.LEFT_OF:
        right = first - 2
        return right - box_w + 1, right
    # NoteOver: span the named participants, widen for text, keep centred.
    lo, hi = (first, last) if first <= last else (last, first)
    left, right = lo - 1, hi + 1
    extra = box_w - (right - left + 1)
    if extra > 0:
        left -= extra // 2
        right += extra - extra // 2
    return left, right


def _render_note(note: Note, layout: DiagramLayout, chars: BoxChars) -> list[str]:
    """Draw a note annotation as a bordered box positioned over or beside its
    participant lifelines. The box obscures any lifelines it covers, while
    lifelines outside it stay continuous."""
    runes = _note_text(note)
    left, right = _note_box_columns(note, layout)
    if left < 0:  # safety; render()'s note gutter should already prevent this
        left = 0

    def border(left_ch: str, right_ch: str) -> str:
        line = _pad_runes(_build_lifeline(layout, chars), right + 1)
        line[left] = left_ch
        for c in range(left + 1, right):
            line[c] = chars.horizontal
        line[right] = right_ch
        return "".join(line).rstrip(" ")

    mid = _pad_runes(_build_lifeline(layout, chars), right + 1)
    for c in range(left, right + 1):  # clear covered lifelines
        mid[c] = " "
    mid[left] = chars.vertical
    mid[right] = chars.vertical
    # Centre the text within the box interior [left+1, right-1].
    inner = right - left - 1
    col = left + 1 + (inner - len(runes)) // 2
    for ch in runes:
        if left < col < right:
            mid[col] = ch
        col += 1

    return [
        border(chars.top_left, chars.top_right),
        "".join(mid).rstrip(" "),
        border(chars.bottom_left, chars.bottom_right),
    ]


def _wrap_fragment(
    frag: Fragment, inner: list[Event], layout: DiagramLayout, chars: BoxChars
) -> list[str]:
    """Render a loop/opt block: paint the inner body, then draw a labelled frame
    around the participants the block touches."""
    # An alt block is split into sections by top-level "else" dividers (dividers
    # nested inside child fragments belong to those fragments). Render each
    # section, leaving a placeholder line where each divider will be drawn once
    # the frame width is known.
    sections, divider_labels = _split_sections(inner)
    body: list[str] = []
    divider_at: dict[int, str] = {}
    for i, sec in enumerate(sections):
        if i > 0:
            divider_at[len(body)] = divider_labels[i - 1]
            body.append("")  # placeholder for the divider line
        body.extend(_render_events(sec, layout, chars))
    # A trailing lifeline gives breathing room above the bottom border.
    body.append(_build_lifeline(layout, chars))

    # The frame spans from just left of the leftmost involved lifeline to just
    # right of the rightmost -- the same participants the block's messages
    # touch. Its left border is pushed further left by the depth of frames
    # nested inside it, so each enclosing frame sits outside its children.
    left_idx, right_idx = _involved_participants(inner, layout)
    left_col = layout.participant_centers[left_idx] - FRAME_INDENT * (_fragment_depth(inner) + 1)
    right_col = layout.participant_centers[right_idx] + FRAME_INDENT

    # A note in the body can extend beyond the participant span (a "left of"
    # note, or one wider than its span). Widen this frame to contain any note
    # box so its border never cuts through it. The margin scales with the
    # note's depth *relative to this frame* (rd) so that when several frames
    # enclose the same note, each outer frame lands FRAME_INDENT columns
    # further out than the one inside it.
    rd = 0
    for ev in inner:
        if ev.kind is EventKind.FRAGMENT_START:
            rd += 1
        elif ev.kind is EventKind.FRAGMENT_END:
            rd -= 1
        elif ev.kind is EventKind.NOTE:
            nl, nr = _note_box_columns(ev.note, layout)
            left_col = min(left_col, nl - 1 - rd * FRAME_INDENT)
            right_col = max(right_col, nr + 1 + rd * FRAME_INDENT)
    left_col = max(left_col, 0)

    # Message labels can extend well past the rightmost lifeline, so widen the
    # frame to clear the longest inner line.
    for line in body:
        right_col = max(right_col, len(line) + 1)

    label = frag.type.value
    if frag.label:
        label += " " + frag.label

    # The label tab ("[label]") sits FRAME_LABEL_INSET cells in from the left
    # corner; make sure the frame is wide enough to hold it (and every "else"
    # divider label) without truncation.
    def widen(text: str) -> None:
        nonlocal right_col
        end = left_col + FRAME_LABEL_INSET + len("[" + text + "]") + 1
        right_col = max(right_col, end)

    widen(label)
    for line_label in divider_labels:
        if line_label:
            widen(line_label)

    out = [_fragment_border(layout, chars, left_col, right_col, label, top=True)]
    for idx, line in enumerate(body):
        divider_label = divider_at.get(idx)
        if divider_label is not None:
            out.append(_fragment_divider(layout, chars, left_col, right_col, divider_label))
        else:
            out.append(_overlay_frame_sides(line, chars, left_col, right_col))
    out.append(_fragment_border(layout, chars, left_col, right_col, "", top=False))
    return out


def _split_sections(inner: list[Event]) -> tuple[list[list[Event]], list[str]]:
    """Divide a fragment body at its top-level "else" dividers, returning the
    section event-lists and the label of the divider preceding each section
    after the first. Dividers nested inside child fragments are left in place
    (they belong to those fragments)."""
    sections: list[list[Event]] = []
    labels: list[str] = []
    cur: list[Event] = []
    depth = 0
    for ev in inner:
        if ev.kind is EventKind.FRAGMENT_START:
            depth += 1
        elif ev.kind is EventKind.FRAGMENT_END:
            depth -= 1
        elif ev.kind is EventKind.FRAGMENT_DIVIDER and depth == 0:
            sections.append(cur)
            labels.append(ev.fragment.label)
            cur = []
            continue
        cur.append(ev)
    sections.append(cur)
    return sections, labels


def _fragment_divider(
    layout: DiagramLayout, chars: BoxChars, left_col: int, right_col: int, label: str
) -> str:
    """An alt "else" divider: a dashed line spanning the frame and joined to its
    side borders, with an optional [label] tab near the left."""
    line = _pad_runes(_build_lifeline(layout, chars), right_col + 1)
    line[left_col] = chars.tee_right
    for c in range(left_col + 1, right_col):
        line[c] = chars.dotted_line
    line[right_col] = chars.tee_left
    if label:
        col = left_col + FRAME_LABEL_INSET
        for ch in "[" + label + "]":
            if col < right_col:
                line[col] = ch
                col += 1
    return "".join(line).rstrip(" ")


def _involved_participants(events: list[Event], layout: DiagramLayout) -> tuple[int, int]:
    """The smallest and largest participant indices referenced by the messages
    in `events`. If there are no messages, spans every participant."""
    min_idx = max_idx = -1
    for ev in events:
        if ev.kind is EventKind.MESSAGE:
            for idx in (ev.message.from_.index, ev.message.to.index):
                if min_idx == -1 or idx < min_idx:
                    min_idx = idx
                if max_idx == -1 or idx > max_idx:
                    max_idx = idx
    if min_idx == -1:
        return 0, len(layout.participant_centers) - 1
    return min_idx, max_idx


def _fragment_border(
    layout: DiagramLayout, chars: BoxChars, left_col: int, right_col: int, label: str, *, top: bool
) -> str:
    """Build a top or bottom frame border on top of a lifeline row, so
    participant lines outside the frame stay continuous. When `top` is true and
    `label` is non-empty, the label is embedded as a "[label]" tab near the
    left corner."""
    line = _pad_runes(_build_lifeline(layout, chars), right_col + 1)

    left_corner = chars.top_left if top else chars.bottom_left
    right_corner = chars.top_right if top else chars.bottom_right
    line[left_col] = left_corner
    for c in range(left_col + 1, right_col):
        line[c] = chars.horizontal
    line[right_col] = right_corner

    if label:
        col = left_col + FRAME_LABEL_INSET
        for ch in "[" + label + "]":
            if col < right_col:
                line[col] = ch
                col += 1
    return "".join(line).rstrip(" ")


def _overlay_frame_sides(line: str, chars: BoxChars, left_col: int, right_col: int) -> str:
    """Draw the left and right vertical borders of a frame onto an
    already-rendered content line."""
    r = _pad_runes(line, right_col + 1)
    r[left_col] = chars.vertical
    r[right_col] = chars.vertical
    return "".join(r).rstrip(" ")


def _pad_runes(s: str, width: int) -> list[str]:
    """`s` as a mutable list of characters, right-padded with spaces to at least
    `width`."""
    r = list(s)
    if len(r) < width:
        r.extend(" " * (width - len(r)))
    return r


def _build_line(participants: list[Participant], layout: DiagramLayout, draw) -> str:
    parts: list[str] = []
    length = 0
    for i in range(len(participants)):
        box_width = layout.participant_widths[i] + BOX_BORDER_WIDTH
        left = layout.participant_centers[i] - box_width // 2
        needed = left - length
        if needed > 0:
            parts.append(" " * needed)
            length += needed
        drawn = draw(i)
        parts.append(drawn)
        length += len(drawn)
    return "".join(parts)


def _build_lifeline(layout: DiagramLayout, chars: BoxChars) -> str:
    line = [" "] * (layout.total_width + 1)
    for c in layout.participant_centers:
        if c < len(line):
            line[c] = chars.vertical
    return "".join(line).rstrip(" ")


def _render_message(msg: Message, layout: DiagramLayout, chars: BoxChars) -> list[str]:
    lines: list[str] = []
    from_ = layout.participant_centers[msg.from_.index]
    to = layout.participant_centers[msg.to.index]

    label = msg.label
    if msg.number > 0:
        label = f"{msg.number}. {msg.label}"

    if label:
        start = min(from_, to) + LABEL_LEFT_MARGIN
        label_width = _width(label)
        w = max(layout.total_width, start + label_width) + LABEL_BUFFER_SPACE
        line = _pad_runes(_build_lifeline(layout, chars), w)
        col = start
        for ch in label:
            if col < len(line):
                line[col] = ch
                col += 1
        lines.append("".join(line).rstrip(" "))

    line = _pad_runes(_build_lifeline(layout, chars), 0)
    style = chars.dotted_line if msg.arrow_type.is_dotted else chars.solid_line

    if from_ < to:
        line[from_] = chars.tee_right
        for i in range(from_ + 1, to):
            line[i] = style
        # Open arrows (-> / -->) have no head: draw the line right up to the
        # target lifeline instead of an arrowhead.
        head, ok = msg.arrow_type.head(chars, True)
        if ok:
            line[to - 1] = head
        # Bidirectional arrows carry a head at the source end too. This can
        # never clobber the target head: participant centers are always ≥6
        # columns apart (box width ≥5 plus spacing ≥1), so from+1 < to-1.
        if msg.arrow_type.is_bidirectional:
            line[from_ + 1] = chars.arrow_left
        line[to] = chars.vertical
    else:
        line[to] = chars.vertical
        line[to + 1] = style
        head, ok = msg.arrow_type.head(chars, False)
        if ok:
            line[to + 1] = head
        for i in range(to + 2, from_):
            line[i] = style
        if msg.arrow_type.is_bidirectional:
            line[from_ - 1] = chars.arrow_right
        line[from_] = chars.tee_left

    # Central connections replace the lifeline attachment with a circle.
    if msg.central_from:
        line[from_] = chars.circle
    if msg.central_to:
        line[to] = chars.circle
    lines.append("".join(line).rstrip(" "))
    return lines


def _render_self_message(msg: Message, layout: DiagramLayout, chars: BoxChars) -> list[str]:
    lines: list[str] = []
    center = layout.participant_centers[msg.from_.index]
    width = layout.self_message_width

    def ensure_width(line: str) -> list[str]:
        target = layout.total_width + width + 1
        return _pad_runes(line, target)

    label = msg.label
    if msg.number > 0:
        label = f"{msg.number}. {msg.label}"

    if label:
        line = ensure_width(_build_lifeline(layout, chars))
        start = center + LABEL_LEFT_MARGIN
        label_width = _width(label)
        needed = start + label_width + LABEL_BUFFER_SPACE
        if len(line) < needed:
            line.extend(" " * (needed - len(line)))
        col = start
        for ch in label:
            if col < len(line):
                line[col] = ch
                col += 1
        lines.append("".join(line).rstrip(" "))

    # Solid arrows keep the solid horizontal glyph; dotted arrows (-->>/-->) use
    # the dotted line.
    style = chars.dotted_line if msg.arrow_type.is_dotted else chars.horizontal

    l1 = ensure_width(_build_lifeline(layout, chars))
    l1[center] = chars.tee_right
    if msg.central_from:
        l1[center] = chars.circle
    for i in range(1, width):
        l1[center + i] = style
    l1[center + width - 1] = chars.self_top_right
    lines.append("".join(l1).rstrip(" "))

    l2 = ensure_width(_build_lifeline(layout, chars))
    l2[center + width - 1] = chars.vertical
    lines.append("".join(l2).rstrip(" "))

    l3 = ensure_width(_build_lifeline(layout, chars))
    l3[center] = chars.vertical
    if msg.central_to:
        l3[center] = chars.circle
    # Open arrows have no head. A bidirectional self-message collapses to a
    # single head: both of its ends sit on the same lifeline, and the return
    # head is where they coincide.
    l3[center + 1] = style
    head, ok = msg.arrow_type.head(chars, False)
    if ok:
        l3[center + 1] = head
    for i in range(2, width - 1):
        l3[center + i] = style
    l3[center + width - 1] = chars.self_bottom
    lines.append("".join(l3).rstrip(" "))

    return lines
