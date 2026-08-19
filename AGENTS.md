# viewmd — implementation notes

A command-line Markdown viewer: renders a `.md` file's headers, tables, code blocks, and other
formatting to ANSI in the terminal, auto-paging into `less` the way `git log`/`bat` do. Design
rationale in [docs/PLAN.md](docs/PLAN.md) (the *why*), the security gate's runbook in
[docs/SECURITY.md](docs/SECURITY.md). This file is the process: how a change gets from idea to a
release.

**It's a Python package** (`viewmd/`, `requires-python = ">=3.10"` in `pyproject.toml`), depending
on `rich` (rendering) and `wcwidth` (display-width math for grid layout — Mermaid diagrams, tables);
dev-only deps are `pytest`, `ruff`, `pip-audit`. The CLI entry point is `viewmd = "viewmd.__main__:main"`
(`pyproject.toml` `[project.scripts]`), runnable in dev via `./viewmd.sh`. Package layout:
`viewmd/render.py` (Markdown → ANSI), `viewmd/mermaid/` (one parser+renderer pair per diagram type —
flowchart, sequence, gantt, pie, kanban, quadrant, packet, ER, gitGraph), `viewmd/preprocessors.py`
and `viewmd/frontmatter.py` (pre-render passes), `viewmd/wikilinks.py`, `viewmd/pager.py` (the `less`
handoff). Maintainer tooling lives in `tools/*.py`/`tools/*.sh`, always invoked via `./tools.sh` (see
below) — never run directly. **`./run-tests.sh` is the whole dev gate in one command**: `pytest`,
`ruff check` (including the security-lint rules, `S`-prefixed, per `docs/SECURITY.md`), `pip-audit`,
and `issues --check`; run it bare before considering any change done, or `./run-tests.sh <pytest args>`
(e.g. `-k render -x`) for a tight iteration loop that skips straight to pytest. Each worktree needs
its own `.venv` (`python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`) since an editable
install is bound to the path it was installed from — `./tools.sh worktree add` bootstraps this
automatically. **When tracing into a dependency's source (e.g. `rich`, `wcwidth`) to understand
how it renders or tokenizes something, look inside the project's own `.venv`
(`.venv/lib/python*/site-packages/<pkg>/`), not a filesystem-wide search** — every dependency
viewmd actually runs against lives there, already pinned to this project's exact installed
version; a broad search can turn up an unrelated copy from some other tool's environment on the
machine and lead to conclusions that don't hold for viewmd's own install.
automatically. Fixtures for byte-for-byte-pinned renderer tests live under `tests/fixtures/`.

**`main` is releases only; `develop` is where issues land.** Every `bug|feature|story/VIEWMD-NNNN`
branch is cut from `develop` and merges back into `develop` (Definition of Done, below) — never
into `main` directly. `main` only advances by merging `develop` into it as an explicit release
step (`git checkout main && git merge --no-ff develop && git tag vX.Y.Z`), matching the version
bump in `CHANGELOG.md`/`pyproject.toml`/`viewmd/__init__.py`. A release is its own explicit
maintainer decision ("cut a release?"), separate from any single issue's landing gate — do not
merge `develop` into `main` as a side effect of closing out an issue. Bump the minor version for
a backward-compatible feature/story, the patch version for a bug fix, matching ordinary semver.
Once tagged and pushed (`git push origin main develop vX.Y.Z`), publish the matching GitHub
release too (`gh release create vX.Y.Z --title vX.Y.Z --notes-file <path>`), using that version's
`CHANGELOG.md` entry verbatim as the release notes — a version bump on `main` without a published
GitHub release is an incomplete release.

**Always invoke `tools/*` scripts through `./tools.sh <tool> [args...]`, never call a script under
`tools/` directly (e.g. never `python3 tools/issues.py` or `python tools/issues.py`).** `./tools.sh`
resolves the repo's own `.venv` regardless of current working directory, so calling a script
directly risks running against the wrong (or no) interpreter/environment. `./tools.sh` with no
arguments lists the available tools.

**Issues live in [issues/](issues/README.md)** — one Markdown file per change (front matter plus
testable prose), stating *what* a change must do, distinct from `docs/` (*why*) and
`CHANGELOG.md` (*when*). Implemented ones move to `issues/archive/` carrying their commit id(s),
rejected ones to `issues/rejected/`. The index in `issues/README.md` is generated and
gate-checked by `./tools.sh issues --check`. **Before adding an issue, run `./tools.sh
issues --check`** — it prints the next free id (`VIEWMD-NNNN`) to name the new file, then
regenerate the index with `./tools.sh issues` once the file is written.

**Every change to the system gets an issue first.** Before writing code for a change (a feature,
a fix, a refactor), create its `VIEWMD-NNNN` file in `issues/` with `status: proposed`, *then*
implement against it, *then* archive it with the commit id. The issue is the *what* the code is
answerable to; writing it first is what keeps its acceptance criteria honest rather than
reverse-engineered from the diff. The one standing exception is a change that is itself only
about an issue (fixing a typo in an issue file, regenerating the index) — that needs no
meta-issue. When in doubt, write the issue.

**A drafted issue is not yet approved to build.** Between `status: proposed` and starting
implementation sits a peer-review gate (the Definition of Ready, [issues/AGILE.md](issues/AGILE.md)):
show the issue to a peer (the human maintainer) and ask outright whether it is accepted. Never
infer acceptance from silence or move straight from drafting to coding. Only once the answer is
yes, fill `accepted_by:`/`accepted_at:` on the issue's front matter and move `status:` to
`in-progress`, in that order, and only then start writing code against it. `./tools.sh issues
--check` enforces the fields are present from `in-progress` onward.

**A finished branch is not yet approved to land.** The Definition of Done ([issues/AGILE.md](issues/AGILE.md))
has the same gate at the other end: once a change is implemented, `run-tests.sh` is green, and it
has been peer-reviewed, do not commit, merge to `develop`, or archive the issue on your own
initiative, however clean the review came back. Show the diff and the review findings to the
maintainer and ask outright, "commit and close this out?" Only on an explicit yes do you commit,
merge into `develop` (`--no-ff`, no squash/rebase), archive the issue, and delete the branch.
Auto-committing small intermediate steps *within* ongoing work is still fine; this gate is
specifically the "ready to land" boundary. **Before asking**, write every review that happened
into the issue's own "Peer review" section (one line per reviewer, agent and maintainer both,
never overwritten): that section is the track record the "commit and close this out?" answer is
based on, not a step that follows it.

**Landing an issue is at least two commits on `develop`, not one.** First, the implementation
commit itself (code + tests + the peer-review lines), made on the `bug|feature|story/VIEWMD-NNNN`
branch and brought into `develop` via the `--no-ff` merge. Second, a separate "Archive
VIEWMD-NNNN, bump to X.Y.Z" commit made directly on `develop` *after* that merge, which: moves the
issue file to `issues/archive/`, sets `status: implemented`, sets `commits:` to the short SHA of
the *implementation* commit (not this archive commit's own SHA, which doesn't exist yet at the
time you're writing the file), sets `changelog:` to the `CHANGELOG.md` anchor (e.g. `"[1.2.0]"`),
bumps `pyproject.toml`/`viewmd/__init__.py`, adds the `CHANGELOG.md` entry, and regenerates the
issues index (`./tools.sh issues`). Only after that second commit is the issue fully closed out on
`develop` — the `main`-merge/tag/GitHub-release step above is still separate again from this.

**Branch naming**: `bug/VIEWMD-NNNN`, `feature/VIEWMD-NNNN`, or `story/VIEWMD-NNNN`, matching the
issue it implements, cut from `develop`.

**Every issue is implemented in its own sibling git worktree, never a plain branch checkout in
the primary working directory — even when it's the only issue in flight.** A single checkout can
only have one branch checked out at a time, so a second agent or editor session working there
would either collide with the first's uncommitted changes or force a branch switch out from under
it. The primary directory needs to stay free at all times so the maintainer can start a parallel
session with any agent the moment they want to, not just when a second issue is already known to
be needed — so this isn't only a "working multiple issues in parallel" rule, it's the default for
starting *any* issue's implementation. `./tools.sh worktree add
VIEWMD-NNNN [bug|feature|story]` (`tools/worktree.sh`) creates `../viewmd-VIEWMD-NNNN` as its own
`git worktree` on the correctly-named branch cut from `develop`, with its own `.venv` bootstrapped
(`pip install -e '.[dev]'`) so `./run-tests.sh`/`./tools.sh` work standalone from it — a `.venv`
is not shareable across worktrees since an editable install is bound to the path it was installed
from. `./tools.sh worktree list` shows every worktree and the `VIEWMD-NNNN` its branch implies;
`./tools.sh worktree remove VIEWMD-NNNN` removes the directory (refusing if it has uncommitted
changes, same as plain `git worktree remove`) but deliberately leaves the branch itself alone —
delete it yourself with `git branch -d` once the work has actually landed on `develop`, so
"stop working here" can never be confused with "throw this away." Point a Claude Code session at
an existing worktree with `EnterWorktree`'s `path:` argument (or just `cd`); point a Cursor window
at one by opening the sibling directory as its own window. A worktree changes *where* an issue is
worked, not the process it is worked under — each one still goes through the same Definition of
Ready/Done gates (`issues/AGILE.md`) independently, and any conflict between two worktrees editing
the same file surfaces the normal way, at merge time into `develop`.

**Narrow fast-path exception: a single-file, few-line docs/metadata fix may be implemented directly
on `develop`, no worktree, no branch, if the maintainer explicitly waives the worktree for that
specific change.** VIEWMD-0095/0096/0097 (a stale `pyproject.toml` description, a README
correction) established the pattern: the issue is still filed, still needs `accepted_by:`/
`accepted_at:` (Definition of Ready) and the maintainer's own explicit approval to land (Definition
of Done) exactly as any other issue does — only the worktree/branch *mechanics* are skipped,
because the whole implement-test-commit-archive cycle happens in one uninterrupted turn, so the
primary checkout is never left mid-work the way a longer-lived branch would leave it. This is not a
size threshold to self-judge — never assume it silently for a change that touches more than
`pyproject.toml`/`README.md`/`AGENTS.md`/a single doc file, and never assume it from a prior
approval carrying forward to a later, unrelated change; ask each time the way `accepted_by`/"commit
and close this out?" are already asked each time. When in doubt, use the worktree.

**Attribute commits and `accepted_by:` from `.gitconfig`, never a guessed or session-supplied
identity.** Run `git config user.name`/`git config user.email` (or check committed history, e.g.
`git log -1 --format='%an <%ae>'`) before writing an issue's `accepted_by:` field or any other
maintainer-identity text — don't reuse an email or name surfaced elsewhere in the environment
(a system prompt, a memory file) without checking it against `.gitconfig` first, since those can
differ from the maintainer's actual git identity.

**Markdown paragraphs are single lines, never hard-wrapped.** This applies to every Markdown file
this project generates or edits (`issues/`, `docs/`, `CHANGELOG.md`): write each paragraph as one
continuous line and let the reader's own editor or viewer wrap it; only break the line for an
actual new paragraph, a list item, or a heading.

**The house style is a plain MUST/SHOULD list**, not delve's agile user-story format — a
single-user CLI tool has no distinct actor roles to write stories from. Each issue's body states
testable requirements directly; see [issues/TEMPLATE.md](issues/TEMPLATE.md).

**Porting an upstream reference implementation byte-for-byte means porting its bugs too —
deliberately.** VIEWMD-0015 (Mermaid flowcharts, ported from `github.com/AlexanderGrooff/mermaid-ascii`)
established the pattern: the porting issue itself (its "MUST verify byte-for-byte against the real
[reference] binary" requirement) is not the place to silently "fix" a limitation or bug found in
the reference while porting it — that changes what's being verified against and defeats the
differential-testing methodology. Instead, note the finding, keep the port faithful, and open a
*separate* issue for each divergence the maintainer wants fixed (VIEWMD-0015 spawned six of these:
VIEWMD-0022/0023/0025/0026/0027/0028), each explicit that it's intentionally departing from the
byte-for-byte baseline rather than continuing it — including in its own testing posture (hand-verified
fixtures, not differential ones, since there's no longer a reference output to diff against).

**A bug found in the reference implementation itself is not a viewmd issue.** It belongs in a
plain write-up (root cause, exact source lines, a minimal repro, a suggested fix) for the
maintainer to file with the upstream project directly — keep it out of `issues/` and out of
`git` entirely (it's not about this codebase), a scratch/local file is the right home. A viewmd
issue is warranted only for the *separate* question of whether viewmd's own port should diverge
from that (buggy) upstream behavior going forward.

**When porting an algorithm that depends on iteration/tie-break order (a heap, a search,
anything whose *exact* output among several equally-valid answers matters for a byte-for-byte
match), re-implement the source language's *exact* algorithm, not just an equivalent one from the
target language's standard library.** VIEWMD-0015 needed this for its A* router: Python's
`heapq` is a different (though also standard) binary-heap implementation than Go's
`container/heap`, and pops equal-priority items in a different order for the same push sequence —
producing a different, equally-valid-looking but non-matching routed path. The fix was porting
`container/heap`'s own push/pop/up/down by hand. A subtler trap inside that same port: Go's `/`
truncates toward zero, Python's `//` floors toward negative infinity — identical for non-negative
operands, silently different for negative ones (e.g. `(-1) / 2` is `0` in Go, `-1` in Python).
A heap's parent-index arithmetic (`(j-1)/2`) hits this exactly at the root; get it wrong and the
heap silently corrupts rather than erroring, only visible as occasional wrong output deep in a
differential-test corpus. Differential-test the specific subroutine standalone (not just the
end-to-end render) when porting anything like this.

**A golden fixture that gets edited to match new output isn't proof of no regression — check it against the pre-change commit, not just `pytest`.** `./run-tests.sh` passing only means a fixture matches whatever the code currently produces; if that fixture is itself part of the diff, a real regression against a byte-for-byte-pinned baseline (per the test file's own docstring, e.g. `tests/test_mermaid_flowchart.py`'s "Rectangle-only fixtures still pin this port byte-for-byte") can pass unnoticed. VIEWMD-0022 shipped exactly this: a "spaces around edge labels" refinement widened a plain `[...]` rectangle fixture that had nothing to do with node shapes, and the golden `.out` file was updated to match rather than preserved — caught only by diffing the new output against the pre-change commit's fixture byte-for-byte during independent review, not by the test suite going green. When a change touches shared layout/sizing code (column widths, row heights, padding), diff every byte-for-byte-pinned fixture against its pre-change version specifically.

**Verify a new rendering feature in composition, not just isolated single-node fixtures.** Each new Mermaid node shape in VIEWMD-0022 got its own one-node fixture and looked correct alone, but real bugs — an inconsistent gap before a diamond's border depending on its tip size, and a diamond's taper failing to reach its own box edge when a sibling rectangle sharing its grid column forced the box wider — only showed up once shapes were rendered next to each other or sharing layout with other nodes, exactly the situations the shipped docs (`docs/diamonds.md`, `docs/mermaid-examples.md`) exercise. Render the actual doc/showcase examples, not just the fixture set, before considering shape/layout work done.

**A "Peer review" line attributed to an agent must be an independent review, not the implementer summarizing its own work.** The Definition of Done ([issues/AGILE.md](issues/AGILE.md)) requires the reviewing agent's pass to be independent of the implementer, in that order before the maintainer's sign-off — a line reading like "implemented X, Y, Z" from the same agent that wrote the code is a work summary, not a review, even when attributed as "(agent)" in the Peer review section. VIEWMD-0022's implementing agent had already added such a line describing its own work before any independent review happened; it didn't satisfy the gate, and a second, genuinely independent pass was still required before the maintainer's sign-off.

**A comprehensive test suite passing is not proof a CLI flag actually works end to end — run the real command with different flag values and diff the output.** VIEWMD-0043 (pie charts) sized its circular rendering by directly querying the raw terminal size instead of using viewmd's already-resolved `--width`, so `--width 60` and `--width 200` against the same file produced byte-identical output. All 384 tests passed the whole time: every test called `render_markdown(..., width=W, ...)` and the render pipeline honestly used whatever `W` it was handed — the bug was that one specific value (`width`) never reached the one renderer that needed it, a plumbing gap invisible to any test that supplies the correct value directly rather than tracing where it comes from. Caught only by the maintainer running `./viewmd.sh file.md --width 60` vs. `--width 200` and comparing by eye. When a feature claims to respect an existing CLI flag, verify it by actually invoking the CLI with different values for that flag, not just by asserting the renderer behaves correctly when handed the value directly.

**A per-cell pattern-match is the wrong shape for "smooth this boundary on a character grid" — sample the boundary densely and let every cell get *some* answer.** VIEWMD-0043's circular pie silhouette went through three designs before one held up: a fixed-width ring in `r²`-space (inconsistent — `r²` isn't linear in radial distance near the edge, so the "ring" came out anywhere from 4 to 32 cells depending on radius, often gapped); per-cell directional tick marks chosen by matching a specific neighbor pattern (fixed the gaps via proper edge detection, but most true boundary cells never matched the pattern at all, reading as scattered disconnected flecks rather than a curve); and finally Unicode quadrant-block glyphs, where every cell independently samples 4 sub-points against the boundary and looks up the one glyph (of 16) matching exactly which are inside — no pattern-matching, so every boundary cell gets a partial-fill glyph, not just the lucky ones. The general lesson: when anti-aliasing a boundary against a discrete grid, prefer "sample N points per cell, direct lookup" over "flag cells matching pattern X" — the latter's coverage is only as good as how often X actually occurs, which is easy to overestimate without actually rendering and looking.

**Don't trust received wisdom about a terminal's capabilities — verify empirically, in that actual terminal, before designing around it.** VIEWMD-0092 initially concluded macOS Terminal.app doesn't support xterm any-motion mouse tracking (mode `1003`), based on its long-standing reputation for click-only support, and started scoping the issue's fallback behavior around that assumption. It was wrong: enabling `\x1b[?1003h` in a real Terminal.app session produces a continuous stream of SGR motion reports exactly as documented, confirmed by having the maintainer run a small raw-escape-sequence probe script and paste back what actually arrived. A terminal-capability claim from memory (or from a tool's general reputation) is a hypothesis, not a fact, until it's been checked against the specific terminal in play — the run skill or a short probe script the maintainer executes directly is worth the extra step before a design decision leans on it.

**Merging two branches that each independently modify the same low-level function can produce a semantic conflict git resolves silently, not just a textual one it flags.** Landing VIEWMD-0093 right after VIEWMD-0080 both touched the interactive pager's shared `loader(width)` callback shape — VIEWMD-0080 added a fourth `body_start` element to its return tuple — and `git merge --no-ff` auto-merged the surrounding code without a conflict marker anywhere, because the two branches never edited the same lines. The break only surfaced as a test failure (`ValueError: too many values to unpack`) immediately after the merge, not during it. Always run `./run-tests.sh` right after every `--no-ff` merge into `develop`, before archiving — a clean auto-merge is not evidence the result is correct, only that git didn't need a human to pick between two textual versions of the same lines.

**A chip/binding with several listed keys isn't automatically "ambiguous" — check whether they produce the same outcome before excluding it from click/hover support.** VIEWMD-0078 grouped `Esc/t cancel` (ToC popup) and `Esc/?/q close help` (help screen) in with genuinely ambiguous chips like `up/down,wheel` (which direction?) and `Enter` (confirms whichever heading happens to be selected — depends on state a synthesized event can't carry), on the reasoning that multiple listed keys means no single unambiguous action to invoke. But `Esc`, `t`, `?`, and `q` in those two chips all produce the *identical* effect (close the overlay) regardless of which one is pressed — multi-key is not the same condition as ambiguous, and conflating them left two clearly-single-outcome chips wired as permanently inert until VIEWMD-0092 caught it in manual testing. When a "no single action" exclusion rule is applied to a new binding, check whether its listed keys actually disagree on outcome, not just whether there's more than one of them.

**A style meant to wrap a whole span can get silently cut short by a `RESET` embedded partway through that span's own existing color codes — check for one, don't assume simple prefix/suffix wrapping is enough.** VIEWMD-0092's `_wrap_hover` opened `_HOVER_STYLE` (reverse video) before a colored span and closed it after, but the span's own content — a keycap chip's `_KEYCAP_BG key _RESET` — carried a full SGR reset partway through, which cancelled the wrapping reverse-video attribute right after the first character, before the wrap's own closing reset was ever reached. Only surfaced in real-terminal manual testing (a unit test asserting `_HOVER_STYLE in out` still passed, since the style byte was present, just not effective for the whole span). When wrapping an arbitrary already-colored string in a new style, either verify it carries no embedded full resets or re-assert the wrapping style after every one found inside it.

Status: actively developed, no stability guarantee yet — the CLI surface (flags, config file format, defaults) still changes most releases; current version tracked in `pyproject.toml`.
