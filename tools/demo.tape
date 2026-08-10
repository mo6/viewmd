# VHS tape for tools/record_demo.sh -- do not run `vhs` on this file directly,
# since it assumes the repo root as its working directory (for `md` and
# docs/example.md) and writes to docs/demo.gif.
#
#   https://github.com/charmbracelet/vhs
Output docs/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 800
Set Theme "Dracula"
Set Padding 20

Type "md docs/example.md"
Enter
Sleep 2s

Down@300ms 10
Sleep 1s
Down@300ms 10
Sleep 1s
Down@300ms 10
Sleep 1s
Down@300ms 10
Sleep 2s

Type "q"
Sleep 1s
