# Decision records

One decision per file, named `NNNN-kebab-title.md`, numbered sequentially.
Start from [0000-template.md](0000-template.md).

Append-only in spirit: do not rewrite history. When a decision changes, write
a new ADR and mark the old one `Superseded by ADR-XXXX`.

An ADR is warranted when the decision is expensive to reverse - architecture,
data contracts, process rules, security posture. Cheap-to-change choices stay
in code review.

## Index

One line per decision, newest last:
`- [NNNN](NNNN-kebab-title.md) - <the decision in one line>`
