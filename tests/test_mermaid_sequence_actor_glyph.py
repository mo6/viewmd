"""Renderer tests for the actor stick-figure glyph (VIEWMD-0020).

Unlike tests/test_mermaid_sequence.py's fixtures, there is no upstream
reference implementation to pin these against -- mermaid-ascii doesn't draw a
distinct actor glyph, and which of ACTOR_FIGURES gets picked is random -- so
these seed `render`'s `rng` argument for determinism instead of using a
golden file that claims outside verification.
"""

import random
from pathlib import Path

from viewmd.mermaid.sequence.parser import parse
from viewmd.mermaid.sequence.renderer import ACTOR_FIGURES, render

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_sequence"


def test_actor_renders_as_three_line_stick_figure_participant_as_box():
    """Structural, not exact-string: which ACTOR_FIGURES entry gets drawn
    shifts whenever a variant is added/removed, so this checks shape/position
    rather than pinning one figure's exact characters."""
    sd = parse(
        "sequenceDiagram\n"
        "    actor U as User\n"
        "    participant CU as Gateway check user\n"
        "    U->>CU: Click Continue button"
    )
    out = render(sd, rng=random.Random(1))  # noqa: S311
    head_row, arms_row, legs_row, label_row, connector_row = out.splitlines()[0:5]

    matches = [f for f in ACTOR_FIGURES
               if f[0] in head_row and f[1] in arms_row and f[2] in legs_row]
    assert len(matches) == 1, f"expected exactly one figure match, got {matches}"

    assert "User" in label_row
    assert "│" in connector_row  # U's connector down to its lifeline

    # CU stays an ordinary box: head/arms rows are blank for it, and its box
    # top merges into the same row as U's legs, per the shared-height design.
    assert "┌" not in head_row and "┐" not in head_row
    assert "┌" not in arms_row and "┐" not in arms_row
    assert "┌────────────────────┐" in legs_row
    assert "│ Gateway check user │" in label_row
    assert "└──────────┬─────────┘" in connector_row


def test_actor_renders_as_stick_figure_ascii():
    sd = parse("sequenceDiagram\nactor A\nparticipant B\nA->>B: hi")
    out = render(sd, use_ascii=True, rng=random.Random(0))  # noqa: S311
    lines = out.splitlines()
    assert "o" in lines[0] or "O" in lines[0]  # A's stick-figure head
    assert "+" in lines[2]  # B's box top border, unaffected


def test_multiple_actors_get_different_figures_before_any_repeat():
    """VIEWMD-0020: 'use different figures when multiple actors are present'
    -- with at least as many actors as variants, every figure is used once
    before any repeats, regardless of shuffle order."""
    names = [f"A{i}" for i in range(len(ACTOR_FIGURES))]
    source = "sequenceDiagram\n" + "\n".join(f"actor {n}" for n in names) + "\n" + (
        "\n".join(f"{names[i]}->>{names[i + 1]}: hi" for i in range(len(names) - 1))
    )
    sd = parse(source)
    out = render(sd, rng=random.Random(42))  # noqa: S311
    head_row, arms_row, legs_row = out.splitlines()[0:3]

    seen = set()
    for figure in ACTOR_FIGURES:
        assert figure[0] in head_row
        assert figure[1] in arms_row
        assert figure[2] in legs_row
        seen.add(figure)
    assert len(seen) == len(ACTOR_FIGURES)


def test_participant_only_diagram_unchanged_by_actor_support():
    """VIEWMD-0020 requirement 4: a diagram with no actors renders identically
    to before this feature existed -- pinned against the real mermaid-ascii
    golden fixture, same as tests/test_mermaid_sequence.py."""
    mmd = (FIXTURES / "participant_alias.mmd").read_text()
    expected_unicode = (FIXTURES / "participant_alias.unicode.out").read_text()
    expected_ascii = (FIXTURES / "participant_alias.ascii.out").read_text()
    sd = parse(mmd)
    assert render(sd, use_ascii=False) == expected_unicode
    assert render(sd, use_ascii=True) == expected_ascii
