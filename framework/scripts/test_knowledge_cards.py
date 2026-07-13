"""Conformance tests for the OKF knowledge cards (stdlib-only).

Every `framework/knowledge/*.md` card must carry an OKF-required `type` in the closed
vocabulary, must not carry the retired `updated` key, and any card with a
`reconcile:` block must parse cleanly via the reconciler's own parser and
drift-govern exactly its `sources` - the guard that the OKF format and the
reconcile format are one and that every sourced card is drift-governed.
"""
import ast
import unittest
from pathlib import Path

from reconcile.frontmatter import parse_frontmatter

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"

# Closed OKF `type` vocabulary for THIS repo (framework/knowledge/README.md is the
# authority). A project adopting the framework extends this set to its own
# card types - same per-project extension-point idiom as `SAFE_BASH` in
# framework/scripts/gnhf_guard.py (see framework/skills/adopt-framework/SKILL.md step 8). Here it
# stays {convention, mechanism}; adopters add their types, test-first.
TYPE_VOCAB = {"convention", "mechanism"}


def cards() -> list[Path]:
    return sorted(p for p in KNOWLEDGE.glob("*.md") if p.name != "README.md")


def frontmatter_lines(text: str) -> list[str]:
    """Return the raw lines of the leading `---`-delimited block, or []."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    out = []
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        out.append(line)
    return []


def top_level_scalar(text: str, key: str) -> str | None:
    """Value of a top-level flat scalar `key:` in the frontmatter, or None."""
    for line in frontmatter_lines(text):
        if line and line[0] not in " \t" and line.split(":", 1)[0].strip() == key:
            parts = line.split(":", 1)
            return parts[1].strip() if len(parts) == 2 else ""
    return None


def strip_inline_comment(value: str) -> str:
    """Drop a trailing ` #...` comment from an unquoted scalar."""
    for i, ch in enumerate(value):
        if ch == "#" and i > 0 and value[i - 1] in " \t":
            return value[:i].rstrip()
    return value.rstrip()


def frontmatter_has_reconcile_key(text: str) -> bool:
    """True when the frontmatter block carries a top-level `reconcile:` key.

    Gated on the parsed frontmatter, not a whole-text substring, so a card
    that only mentions `reconcile:` in its body prose does not false-trip.
    """
    for line in frontmatter_lines(text):
        if line and line[0] not in " \t" and line.split(":", 1)[0].strip() == "reconcile":
            return True
    return False


def top_level_sources(text: str) -> set[str]:
    """The card's `sources` list as a set of paths (JSON-style flat list)."""
    value = top_level_scalar(text, "sources")
    if not value:
        return set()
    return set(ast.literal_eval(value))


class KnowledgeCardTest(unittest.TestCase):
    def test_cards_exist(self):
        self.assertTrue(cards(), "expected at least one knowledge card")

    def test_every_card_has_parseable_frontmatter(self):
        for card in cards():
            with self.subTest(card=card.name):
                self.assertTrue(
                    frontmatter_lines(card.read_text(encoding="utf-8")),
                    "missing --- delimited frontmatter",
                )

    def test_every_card_has_type_in_vocab(self):
        for card in cards():
            with self.subTest(card=card.name):
                value = top_level_scalar(card.read_text(encoding="utf-8"), "type")
                self.assertIsNotNone(value, "missing OKF-required `type`")
                self.assertIn(strip_inline_comment(value), TYPE_VOCAB)

    def test_no_card_carries_retired_updated_key(self):
        for card in cards():
            with self.subTest(card=card.name):
                self.assertIsNone(
                    top_level_scalar(card.read_text(encoding="utf-8"), "updated"),
                    "retired `updated` key still present; rename to `timestamp`",
                )

    def test_reconcile_blocks_parse_via_reconciler(self):
        for card in cards():
            with self.subTest(card=card.name):
                text = card.read_text(encoding="utf-8")
                if not frontmatter_has_reconcile_key(text):
                    continue
                doc = parse_frontmatter(text)
                self.assertIsNotNone(doc, "reconcile block did not parse")
                self.assertIsNone(doc.error, doc.error)
                self.assertIsNotNone(doc.direction)

    def test_reconcile_governs_equal_sources(self):
        """Every sourced card is drift-governed with one binding per source:
        the set of `governs` across its bindings equals its `sources` set."""
        for card in cards():
            with self.subTest(card=card.name):
                text = card.read_text(encoding="utf-8")
                if not frontmatter_has_reconcile_key(text):
                    continue
                doc = parse_frontmatter(text)
                self.assertIsNotNone(doc, "reconcile block did not parse")
                self.assertIsNone(doc.error, doc.error)
                self.assertEqual(
                    {b.governs for b in doc.bindings},
                    top_level_sources(text),
                    "reconcile `governs` set must equal the card's `sources`",
                )


if __name__ == "__main__":
    unittest.main()
