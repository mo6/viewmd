---
title: "Advanced Frontmatter Features"
description: A realistic blog-post-style front matter combining several advanced features at once
published: true
draft: no
date: 2026-08-03T09:00:00-05:00
tags:
  - javascript
  - react
  - markdown
authors:
  - name: John Doe
    email: john@example.com
  - name: Jane Smith
    email: jane@example.com
seo:
  title: Custom SEO Title
  description: A custom description for search engines
social:
  twitter:
    card: summary_large_image
difficulty: intermediate
reading_time: 8
summary: |
  This post covers advanced frontmatter
  across several dimensions at once.
---

# Advanced frontmatter, combined

This mirrors the shape of the reference page's own end-to-end example: scalars, a plain
`[a, b, c]`-style list would have been the "easy" case, but here `tags` and `authors` use the
dash-list and array-of-objects forms, `seo`/`social` are nested objects, `draft` uses the `no`
boolean alias, `date` is full ISO 8601 with a negative UTC offset, and `summary` is a literal
block scalar. Check the front-matter table against this file's actual intent end to end.
