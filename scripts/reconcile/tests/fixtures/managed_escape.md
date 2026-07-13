---
reconcile:
  direction: code-is-truth
  bindings:
    - doc_anchor: escape
      governs: ../../../etc/passwd
---

# Escaping binding

<!-- reconcile:escape:start -->
This binding names a path outside the repo; the plan must surface an error,
never crash and never read outside root.
<!-- reconcile:escape:end -->
