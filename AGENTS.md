# viewmd — implementation notes

A command-line Markdown viewer: renders a `.md` file's headers, tables, code blocks, and other
formatting to ANSI in the terminal, auto-paging into `less` the way `git log`/`bat` do. Design
rationale in [docs/PLAN.md](docs/PLAN.md) (the *why*), the security gate's runbook in
[docs/SECURITY.md](docs/SECURITY.md). This file is the process: how a change gets from idea to a
release.

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

**Working multiple issues in parallel uses a sibling git worktree per issue, not multiple
sessions in the one working directory.** A single checkout can only have one branch checked out
at a time, so a second agent or editor session working there would either collide with the
first's uncommitted changes or force a branch switch out from under it. `./tools.sh worktree add
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

Status: pre-1.0, in initial development.
