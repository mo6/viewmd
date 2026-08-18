---
id: VIEWMD-0082
title: Click-to-follow fails for a path-qualified wikilink target outside the vault root
status: in-progress
area: [pager]
effort: low
created: 2026-08-18
updated: 2026-08-18
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-18
commits: []
related: [VIEWMD-0076]
supersedes: []
changelog:
reason:
---

# Click-to-follow fails for a path-qualified wikilink target outside the vault root

## Summary

A `[[Target|Display]]` wikilink whose target is a full vault-relative path (Obsidian's own
disambiguation form, e.g. `[[Projects/Garden/Notes/_Index|Notes]]`) fails to
click-navigate whenever the note containing the link isn't itself sitting at the vault root --
`_resolve_link_target`'s wikilink branch resolves the path relative to the *linking note's own
directory*, not the vault root, so the join produces a nonexistent path and the click is a silent
no-op.

## Motivation / problem

`_resolve_link_target()` (`viewmd/interactive_pager.py:511-524`) documents its own scope as
resolving "the way Obsidian does for a flat vault": try `f"{target}.md"` directly in `current_dir`
(the linking document's own directory), then fall back to a recursive `os.walk(current_dir)`
search for a file whose *basename* matches `f"{target}.md"`. That works for a bare note name
(`[[Notes]]`), but Obsidian doesn't always emit a bare name -- when two notes share a name, or a
user has "always use full path" configured, it links via the note's full vault-relative path
instead (`[[Projects/Garden/Notes/_Index|Notes]]`). For a target containing `/`:

- The "direct" `os.path.join(current_dir, f"{target}.md")` check only succeeds when
  `current_dir` happens to *be* the vault root -- for a linking note anywhere else in the tree
  (including inside the very path the target names, a common case for a folder's own `_Index.md`
  linking to a sibling subfolder), it joins the target path onto the wrong base and resolves to a
  path that doesn't exist.
- The `os.walk(current_dir)` fallback checks `f"{target}.md" in files`, but `files` (from
  `os.walk`) holds bare filenames with no directory component -- a target string containing `/`
  can never appear in that list, so this fallback can never match a path-qualified target either,
  regardless of where `current_dir` is rooted.

The result: the link renders (colored, underlined, a real OSC8 span -- confirmed by direct
testing), but clicking it does nothing, with no echo-area message explaining why, indistinguishable
from a broken/missing link.

## Requirements

1. MUST make `_resolve_link_target` resolve a path-qualified wikilink target (one containing `/`)
   to the correct file when the linking note is *not* at the vault root, for the common case
   where every ancestor directory of `current_dir` up to (and including) the actual vault root is
   on the filesystem path between them -- i.e. searching upward from `current_dir` through each
   ancestor, trying `os.path.join(ancestor, f"{target}.md")` at each level, succeeds once it
   reaches the vault root.
2. MUST NOT change resolution of a bare (no `/`) wikilink target -- the existing direct-then-
   `os.walk` behavior for `[[Notes]]`-style targets is unaffected.
3. MUST NOT change resolution of an ordinary (non-`wikilink:`) relative Markdown link href --
   `_resolve_link_target`'s non-wikilink branch is out of scope.
4. MUST bound the upward search so it cannot walk past the filesystem root or loop -- stop once
   `os.path.dirname(ancestor) == ancestor`.
5. SHOULD prefer the nearest matching ancestor (search outward from `current_dir`, return on the
   first match) over any more distant one, so a false-positive match under an unrelated parent
   directory sharing a coincidental path segment is less likely to win over the intended target.

## Non-goals

- Tracking an explicit "vault root" concept anywhere in viewmd -- this fix works by walking
  ancestors opportunistically, not by teaching viewmd what a vault is.
- Fixing the pre-existing `os.walk` fallback's own known issues (unbounded/uncached recursive
  walk on every click, ambiguous multi-match resolution) -- out of scope for this bug, which is
  about a target that currently can't resolve at all, not about improving an already-partially-
  working path.
- Any change to `viewmd/wikilinks.py`'s rewrite pass -- the href it produces is already correct;
  only its resolution in the interactive pager is broken.

## Design notes / links

`_resolve_link_target()`, `viewmd/interactive_pager.py:511-524`. Reproduced directly: `_load()` +
`_link_at()` confirm the href (`wikilink:Projects/Garden/Notes/_Index`, correctly
percent-decoded) is present and clickable-looking; `_resolve_link_target(href, nested_doc_dir)`
returns `None` whenever `nested_doc_dir` isn't the exact vault root, even though the target file
exists on disk at the expected path from that root.

## Acceptance / verification

- New unit tests in `tests/test_interactive_pager.py` (alongside the existing
  `test_resolve_link_target_*` tests) covering: a path-qualified wikilink target resolves
  correctly when `current_dir` is several levels below the vault root; still resolves when
  `current_dir` is the vault root itself (today's already-working case); returns `None` when no
  ancestor has a matching file; a bare (no `/`) wikilink target's resolution is unchanged.
- `./run-tests.sh` green.

## Peer review

- **code-review agent** (agent), 2026-08-18: one finding, the new ancestor-walk branch built
  `os.path.join(ancestor, f"{target}.md")` from a document-controlled `target` without rejecting
  an absolute or `..`-escaping target, letting a crafted `[[/etc/passwd|x]]`-style wikilink
  resolve (and then open) any `.md`-suffixed path reachable on disk -- the same class of escape
  the non-wikilink branch already guards against. Fixed inline (reject `os.path.isabs(target)` or
  any `..` path segment before the ancestor walk), with regression tests added.
