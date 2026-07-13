---
reconcile:
  direction: code-is-truth
  bindings:
    - doc_anchor: cached-behavior
      governs: decorated.py
      code_anchor: "def cached"
---

# Cached

<!-- reconcile:cached-behavior:start -->
`cached(n)` memoizes a single result via `@lru_cache(maxsize=1)`.
<!-- reconcile:cached-behavior:end -->
