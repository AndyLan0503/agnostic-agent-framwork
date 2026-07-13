"""Conformance tests for the OKF knowledge cards (stdlib-only).

Every `framework/knowledge/*.md` card must carry an OKF-required `type` in the closed
vocabulary, must not carry the retired `updated` key, and any card with a
`knowform:` block must declare a valid drift `direction` and drift-govern
exactly its `sources` - the guard that the OKF format and the knowform drift
format are one and that every sourced card is drift-governed. The knowform
tool itself is external (https://pypi.org/project/knowform/); this repo keeps
`knowform.lock` in sync via `knowform sync`, so the check here parses the
`knowform:` frontmatter with the stdlib alone rather than importing the tool.
"""
import ast
import unittest
from pathlib import Path

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"

# Closed OKF `type` vocabulary for THIS repo (framework/knowledge/README.md is the
# authority). A project adopting the framework extends this set to its own
# card types - same per-project extension-point idiom as `SAFE_BASH` in
# framework/scripts/gnhf_guard.py (see framework/skills/adopt-framework/SKILL.md step 8). Here it
# stays {convention, mechanism}; adopters add their types, test-first.
TYPE_VOCAB = {"convention", "mechanism"}

# The knowform drift `direction` enum (mirrors knowform's own vocabulary).
DIRECTIONS = {"code-is-truth", "doc-is-truth", "manual"}


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


def frontmatter_has_knowform_key(text: str) -> bool:
    """True when the frontmatter block carries a top-level `knowform:` key.

    Gated on the parsed frontmatter, not a whole-text substring, so a card
    that only mentions `knowform:` in its body prose does not false-trip.
    """
    for line in frontmatter_lines(text):
        if line and line[0] not in " \t" and line.split(":", 1)[0].strip() == "knowform":
            return True
    return False


def knowform_body(text: str) -> list[str]:
    """Lines nested under the top-level `knowform:` frontmatter key."""
    body: list[str] = []
    in_block = False
    base_indent = 0
    for line in frontmatter_lines(text):
        if not line.strip() or line.lstrip().startswith("#"):
            if in_block:
                body.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        if not in_block:
            if indent == 0 and line.split(":", 1)[0].strip() == "knowform":
                in_block = True
                base_indent = indent
            continue
        if indent <= base_indent:
            break
        body.append(line)
    return body


def knowform_direction(text: str) -> str | None:
    """The `direction:` scalar inside the `knowform:` block, or None."""
    for line in knowform_body(text):
        stripped = line.strip()
        if stripped.split(":", 1)[0].strip() == "direction":
            return strip_inline_comment(stripped.split(":", 1)[1].strip())
    return None


def knowform_governs(text: str) -> set[str]:
    """The set of `governs:` paths across the `knowform:` bindings."""
    out = set()
    for line in knowform_body(text):
        stripped = line.strip().lstrip("-").strip()
        if stripped.split(":", 1)[0].strip() == "governs":
            out.add(strip_inline_comment(stripped.split(":", 1)[1].strip()))
    return out


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

    def test_knowform_blocks_declare_valid_direction(self):
        """Every `knowform:` block parses (stdlib) to a valid drift direction
        and names at least one governed source."""
        for card in cards():
            with self.subTest(card=card.name):
                text = card.read_text(encoding="utf-8")
                if not frontmatter_has_knowform_key(text):
                    continue
                self.assertIn(
                    knowform_direction(text),
                    DIRECTIONS,
                    "knowform block missing or invalid `direction`",
                )
                self.assertTrue(
                    knowform_governs(text),
                    "knowform block governs no source",
                )

    def test_knowform_governs_equal_sources(self):
        """Every sourced card is drift-governed with one binding per source:
        the set of `governs` across its bindings equals its `sources` set."""
        for card in cards():
            with self.subTest(card=card.name):
                text = card.read_text(encoding="utf-8")
                if not frontmatter_has_knowform_key(text):
                    continue
                self.assertEqual(
                    knowform_governs(text),
                    top_level_sources(text),
                    "knowform `governs` set must equal the card's `sources`",
                )


if __name__ == "__main__":
    unittest.main()
