"""Conformance tests for the OKF knowledge cards and their drift bindings.

Two formats meet here and neither may drift from the other:

* a card is a plain OKF document - required `type` from a closed vocabulary,
  no retired keys, and a body under one `## Fact` heading;
* a drift binding is an entry in `knowform.bindings.json`, out-of-band, so the
  card carries no tool-specific markup.

The invariant tying them together is unchanged from the inline era: every
sourced card is drift-governed once per `sources` entry, so a card's claim is
always checked against the file that proves it.

knowform itself is external (https://pypi.org/project/knowform/), so this
module parses frontmatter, headings and blocks with the stdlib rather than
importing the tool - the suite must run on the stock macOS Python 3.9 before
`make setup` has installed anything.

Per `framework/knowledge/checks-report-what-they-examined.md`, every check here
reports what it examined and refuses to pass on an empty scan set: a green
knowledge-card suite that found no cards, or a binding check that found no
bindings, is the failure this file exists to make impossible.
"""

from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE = ROOT / "framework" / "knowledge"
MANIFEST = ROOT / "knowform.bindings.json"

# Closed OKF `type` vocabulary for THIS repo (framework/knowledge/README.md is the
# authority). A project adopting the framework extends this set to its own
# card types - same per-project extension-point idiom as `SAFE_BASH` in
# framework/scripts/gnhf_guard.py (see framework/skills/adopt-framework/SKILL.md step 8). Here it
# stays {convention, mechanism}; adopters add their types, test-first.
TYPE_VOCAB = {"convention", "mechanism"}

# The knowform drift `direction` enum (mirrors knowform's own vocabulary).
DIRECTIONS = {"code-is-truth", "doc-is-truth", "manual"}

# The single heading every card body opens with. Bindings address a card by
# this heading path, so a card that renames or splits it silently detaches
# every binding pointing at it - which is why the shape is asserted here.
BODY_HEADING = "Fact"

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def cards() -> list:
    return sorted(p for p in KNOWLEDGE.glob("*.md") if p.name != "README.md")


def frontmatter_lines(text: str) -> list:
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


def body_lines(text: str) -> list:
    """The card's lines after the leading frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1:]
    return []


def top_level_scalar(text: str, key: str):
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


def top_level_sources(text: str) -> set:
    """The card's `sources` list as a set of paths (JSON-style flat list)."""
    value = top_level_scalar(text, "sources")
    if not value:
        return set()
    return set(ast.literal_eval(value))


def headings(lines: list) -> list:
    """(level, text) for ATX headings outside fenced code blocks."""
    out, in_fence = [], False
    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING.match(line)
        if match:
            out.append((len(match.group(1)), match.group(2).strip()))
    return out


def blocks_under_body(lines: list) -> list:
    """Blank-line-separated blocks of the card body, a fenced block counted as
    one. Mirrors how knowform narrows a binding with `block: N`, so a stale
    index fails here rather than silently binding the wrong paragraph."""
    content = []
    seen_heading = False
    for line in lines:
        if not seen_heading:
            match = _HEADING.match(line)
            if match and match.group(2).strip() == BODY_HEADING:
                seen_heading = True
            continue
        content.append(line)
    out, current, in_fence = [], [], False
    for line in content:
        if _FENCE.match(line):
            in_fence = not in_fence
            current.append(line)
            continue
        if not in_fence and not line.strip():
            if current:
                out.append(current)
                current = []
            continue
        current.append(line)
    if current:
        out.append(current)
    return out


def manifest_bindings() -> list:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return data.get("markdown", [])


class KnowledgeCardTest(unittest.TestCase):
    def test_cards_exist(self):
        self.assertTrue(cards(), f"expected at least one knowledge card in {KNOWLEDGE}")

    def test_every_card_has_parseable_frontmatter(self):
        found = cards()
        self.assertTrue(found, "no cards examined")
        for card in found:
            with self.subTest(card=card.name):
                self.assertTrue(
                    frontmatter_lines(card.read_text(encoding="utf-8")),
                    "missing --- delimited frontmatter",
                )

    def test_every_card_has_type_in_vocab(self):
        found = cards()
        self.assertTrue(found, "no cards examined")
        for card in found:
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

    def test_no_card_carries_retired_inline_knowform_markup(self):
        """knowform 0.3 reads bindings only from `knowform.bindings.json`. An
        inline `knowform:` frontmatter block or a `<!-- knowform:... -->` anchor
        is markup nothing consumes, and a binding declared there is a binding
        that silently does not exist."""
        for card in cards():
            with self.subTest(card=card.name):
                text = card.read_text(encoding="utf-8")
                self.assertIsNone(
                    top_level_scalar(text, "knowform"),
                    "retired inline `knowform:` frontmatter block; declare the "
                    "binding in knowform.bindings.json instead",
                )
                self.assertNotIn(
                    "<!-- knowform:", text,
                    "retired inline knowform anchor marker; bindings address a "
                    "card by heading path now",
                )

    def test_every_card_body_has_exactly_one_fact_heading(self):
        found = cards()
        self.assertTrue(found, "no cards examined")
        for card in found:
            with self.subTest(card=card.name):
                found_headings = headings(body_lines(card.read_text(encoding="utf-8")))
                self.assertEqual(
                    found_headings, [(2, BODY_HEADING)],
                    f"a card body is exactly one `## {BODY_HEADING}` section - "
                    f"bindings address it by that heading path, and 'one fact "
                    f"per card' means a card needing more sections is two cards. "
                    f"Found: {found_headings}",
                )


class DriftBindingTest(unittest.TestCase):
    """`knowform.bindings.json` is the whole binding set; nothing is inline."""

    def setUp(self):
        self.assertTrue(
            MANIFEST.exists(),
            f"{MANIFEST.name} is missing - every card binding lives there now",
        )
        self.bindings = manifest_bindings()
        self.assertTrue(
            self.bindings,
            f"{MANIFEST.name} declares no markdown bindings. `make reconcile` "
            f"would report success while checking nothing.",
        )

    def test_every_binding_is_well_formed(self):
        for binding in self.bindings:
            with self.subTest(binding=binding.get("governs")):
                for key in ("doc", "heading", "governs"):
                    self.assertIn(key, binding, f"binding missing `{key}`")
                self.assertIn(
                    binding.get("direction"), DIRECTIONS,
                    f"invalid drift direction {binding.get('direction')!r}",
                )
                self.assertTrue(
                    (ROOT / binding["doc"]).exists(),
                    f"binding doc {binding['doc']!r} does not exist",
                )
                self.assertTrue(
                    (ROOT / binding["governs"]).exists(),
                    f"binding governs {binding['governs']!r}, which does not exist",
                )

    def test_every_binding_anchor_resolves(self):
        """A heading path that matches nothing, or a `block` index past the end
        of the section, is a binding pointing at no text."""
        for binding in self.bindings:
            with self.subTest(binding=f"{binding['doc']}->{binding['governs']}"):
                lines = body_lines((ROOT / binding["doc"]).read_text(encoding="utf-8"))
                texts = [text for _, text in headings(lines)]
                for step in binding["heading"]:
                    self.assertIn(
                        step, texts,
                        f"heading {step!r} not found in {binding['doc']}",
                    )
                block = binding.get("block")
                if block is not None:
                    available = blocks_under_body(lines)
                    self.assertTrue(
                        1 <= block <= len(available),
                        f"block {block} is out of range in {binding['doc']} "
                        f"({len(available)} blocks under `## {BODY_HEADING}`)",
                    )

    def test_governs_set_equals_sources_for_every_sourced_card(self):
        """The invariant carried over from the inline era: every sourced card is
        drift-governed with one binding per source, in both directions."""
        by_doc = {}
        for binding in self.bindings:
            by_doc.setdefault(binding["doc"], set()).add(binding["governs"])

        examined = 0
        for card in cards():
            sources = top_level_sources(card.read_text(encoding="utf-8"))
            if not sources:
                continue
            examined += 1
            rel = card.relative_to(ROOT).as_posix()
            with self.subTest(card=card.name):
                self.assertEqual(
                    by_doc.get(rel, set()), sources,
                    f"{card.name} lists sources {sorted(sources)} but "
                    f"{MANIFEST.name} governs {sorted(by_doc.get(rel, set()))}. "
                    f"Every sourced card is bound once per source.",
                )
        self.assertTrue(
            examined, "no sourced cards examined - nothing was checked"
        )

    def test_every_binding_points_at_a_knowledge_card(self):
        """Guards the reverse direction: a binding whose doc is not a card would
        never be covered by the sources check above."""
        known = {c.relative_to(ROOT).as_posix() for c in cards()}
        for binding in self.bindings:
            with self.subTest(doc=binding["doc"]):
                self.assertIn(
                    binding["doc"], known,
                    f"{binding['doc']!r} is not a knowledge card",
                )


if __name__ == "__main__":
    unittest.main()
