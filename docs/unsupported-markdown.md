# Unsupported Markdown features

What viewmd doesn't render specially, checked directly against a `.md` file and against
[Obsidian's Flavored Markdown reference](https://obsidian.md/help/obsidian-flavored-markdown)
(CommonMark + GFM + LaTeX, plus Obsidian's own additions). Each one currently falls through to
Rich's default: printed as literal source text, no special styling or structure. This is a
survey, not a backlog — see `docs/PLAN.md`'s "Out of scope" section for the standing policy
("add support only against a real `.md` file that needs it, not speculatively").

| Feature | Syntax | Renders as |
|---|---|---|
| Footnotes | `[^id]`, `[^id]: text` | Literal text, no superscript, no collected list |
| Highlight / mark | `==text==` | Literal text, no styling |
| Comments | `%%text%%` | Literal text, not hidden |
| Block identifiers | `^id` | Literal text, no linking |
| Block references | `![[Link#^id]]` | Literal text |
| Note embeds | `![[Note]]` | Falls through to Rich's generic image placeholder; does not inline the target's content |
| Math (LaTeX) | `$x^2$`, `$$...$$` | Literal text, not typeset |
| Definition lists | `Term`\n`:   definition` | Collapses into one flowed paragraph |
| Tags | `#tag` | Literal text, no color/link (Obsidian's separate Tags page, not the OFM page) |

For contrast, the Obsidian-specific features viewmd *does* implement: wikilinks (`[[Link]]`,
VIEWMD-0006), admonition callouts (`> [!note]`, VIEWMD-0059/0060), and GFM task checkboxes
(`- [ ]`/`- [x]`, VIEWMD-0058) — plus everything Rich's CommonMark/GFM core already covers
(tables, strikethrough, fenced code, etc.).

## Relative implementation cost

viewmd extends Rich's Markdown two ways (see `docs/PLAN.md`): a text-level preprocessing pass
before the body reaches Rich (`wikilinks.py`'s approach), or subclassing one of Rich's per-token
element renderers (`render.py`'s `ViewmdBlockQuote`/`ViewmdCodeBlock`/`ViewmdListItem`, wired
into `ViewmdMarkdown.elements`). The second only works for tokens `markdown-it-py`'s CommonMark
core already emits (blockquote, list item, fence, ...); none of the features below get a token
from that core parser, so all of them would need the first approach.

**Relatively easy** — pure text preprocessing, no new Rich style needed:
- **Comments (`%%...%%`)**: delete the matched span, fence/code-span aware exactly like
  `wikilinks.py` already is. No rendering decision to make.
- **Tags (`#tag`)**: rewrite into the same fake-link trick `wikilinks.py` uses
  (`[#tag](<wikilink:...>)`) to pick up `markdown.link_url` styling for free. Main care point:
  distinguishing `#tag` from an ATX heading (`# Heading`) and from `#` inside code/URLs.

**Medium** — text preprocessing, but no ready-made Rich style to reuse:
- **Highlight (`==text==`)**: Rich's Markdown has no built-in "mark" style, so there's nothing
  to plug into cleanly; would need either a new style definition or some reuse of an existing
  one that doesn't already carry the wrong meaning (bold, code).
- **Footnotes (`[^id]` / `[^id]: text`)**: needs a real preprocessing pass — collect
  definitions, strip them from the body, renumber/replace inline refs, append a rendered
  footnotes section. Shaped like `mermaid/preprocess.py`'s block-extraction pass, just for an
  inline+trailing-section construct instead of a fenced block.

**Hard** — cross-references or capabilities viewmd doesn't have yet:
- **Block identifiers/references (`^id`, `![[Link#^id]]`)**: requires indexing blocks (within a
  file and potentially across files) and resolving a reference to a specific block's rendered
  output — no existing mechanism in viewmd does cross-block or cross-file resolution.
- **Real note/image embeds (`![[Note]]`)**: requires vault-relative path resolution, recursive
  render (with cycle detection), and for images, actual terminal image support (sixel/kitty
  protocol) — a materially bigger feature than a text rewrite.
- **Math (`$x^2$`, `$$...$$`)**: typesetting LaTeX as readable ANSI text is not a small
  preprocessing step; arguably out of scope for a terminal tool the way image-to-ASCII already
  is (`docs/PLAN.md`'s "Out of scope").
