# viewmd — implementation notes

A command-line Markdown viewer: renders a `.md` file's headers, tables, code blocks, and other
formatting to ANSI in the terminal, auto-paging into `less` the way `git log`/`bat` do. Design
rationale in [docs/PLAN.md](docs/PLAN.md) (the *why*). This file is the process: how a change
gets from idea to a release.

**`main` is releases only; `develop` is where issues land.** Every `bug|feature|story/VIEWMD-NNNN`
branch is cut from `develop` and merges back into `develop` (Definition of Done, below) — never
into `main` directly. `main` only advances by merging `develop` into it as an explicit release
step (`git checkout main && git merge --no-ff develop && git tag vX.Y.Z`), matching the version
bump in `CHANGELOG.md`/`pyproject.toml`/`viewmd/__init__.py`. A release is its own explicit
maintainer decision ("cut a release?"), separate from any single issue's landing gate — do not
merge `develop` into `main` as a side effect of closing out an issue.

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

**Branch naming**: `bug/VIEWMD-NNNN`, `feature/VIEWMD-NNNN`, or `story/VIEWMD-NNNN`, matching the
issue it implements, cut from `develop`.

**Markdown paragraphs are single lines, never hard-wrapped.** This applies to every Markdown file
this project generates or edits (`issues/`, `docs/`, `CHANGELOG.md`): write each paragraph as one
continuous line and let the reader's own editor or viewer wrap it; only break the line for an
actual new paragraph, a list item, or a heading.

**The house style is a plain MUST/SHOULD list**, not delve's agile user-story format — a
single-user CLI tool has no distinct actor roles to write stories from. Each issue's body states
testable requirements directly; see [issues/TEMPLATE.md](issues/TEMPLATE.md).

Status: pre-1.0, in initial development.
