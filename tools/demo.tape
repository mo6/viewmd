# VHS tape for tools/record_demo.sh -- do not run `vhs` on this file directly,
# since it assumes the repo root as its working directory (for `md` and
# docs/example.md) and writes to docs/demo.gif.
#
#   https://github.com/charmbracelet/vhs
Output docs/demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1100
Set Height 780
Set Theme "Dracula"
Set Padding 10
Set Framerate 1

# tools/demo-pages/*.md splits docs/example.md into one-topic-per-page files
# that each fit on one screen; tools/demo_pages_loop.sh shows each in turn via
# `md` (less -F auto-advances since the page fits) with a 5s pause between.
Type "./tools/demo_pages_loop.sh"
Enter
Sleep 55s
