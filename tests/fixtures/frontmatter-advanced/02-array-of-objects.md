---
title: Array of objects test
authors:
  - name: John Doe
    email: john@example.com
  - name: Jane Smith
    email: jane@example.com
---

# Array of objects

The `authors` key above is a YAML list whose items are themselves mappings (`name`/`email`
pairs), not plain scalars. Check whether the front-matter table shows both authors with their
fields, shows only partial data, or shows the raw YAML text.
