---
title: Nested objects test
seo:
  title: Custom SEO Title
  description: A custom description for search engines
  keywords: [markdown, frontmatter, testing]
social:
  twitter:
    card: summary_large_image
    creator: "@example"
  og:
    type: article
    image: /images/cover.png
---

# Nested objects

The `seo` and `social` keys above are YAML mappings nested under a top-level key, not flat `key: value` pairs. Check whether the front-matter table shows the nested structure meaningfully, shows it as raw indented text, or drops it.
