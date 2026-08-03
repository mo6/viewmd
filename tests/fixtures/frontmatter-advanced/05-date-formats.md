---
title: Date formats test
published_iso: 2026-08-03T14:30:00+02:00
published_date_only: 2026-08-03
published_quoted: "2026-08-03"
updated_iso_utc: 2026-08-03T12:30:00Z
---

# Date formats

Four date-shaped values: full ISO 8601 with a timezone offset, a bare `YYYY-MM-DD`, the same
bare date as a quoted string, and ISO 8601 in UTC (`Z` suffix). Check whether all four render as
readable dates, whether the unquoted ones are misparsed (e.g. `:` inside the value confused for a
new key), and whether quoted vs. unquoted dates render differently from each other.
