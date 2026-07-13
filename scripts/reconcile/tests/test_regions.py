import unittest
from pathlib import Path

from reconcile.frontmatter import Binding
from reconcile.regions import (
    hash_span, normalize, resolve_code_region, resolve_doc_region,
    resolve_governed_files,
)

FIX = Path(__file__).parent / "fixtures"


class NormalizeHashTest(unittest.TestCase):
    def test_normalize_strips_and_trims(self):
        self.assertEqual(normalize("\n\n  a  \nb   \n\n"), "  a\nb")

    def test_normalize_line_endings(self):
        self.assertEqual(normalize("a\r\nb\r\n"), "a\nb")

    def test_hash_is_stable_under_trailing_ws(self):
        self.assertEqual(hash_span("a\nb"), hash_span("a  \nb\n\n"))

    def test_hash_differs_on_content(self):
        self.assertNotEqual(hash_span("a"), hash_span("b"))

    def test_hash_prefix(self):
        self.assertTrue(hash_span("x").startswith("sha256:"))


class DocRegionTest(unittest.TestCase):
    def test_fenced_region(self):
        b = Binding(doc_anchor="add-behavior", governs="calc.py")
        region = resolve_doc_region(FIX, Path("managed_add.md"), b)
        self.assertFalse(region.whole)
        self.assertIn("returns the sum", region.text(FIX))

    def test_absent_fence_degrades_to_whole(self):
        b = Binding(doc_anchor="overview", governs="calc.py")
        region = resolve_doc_region(FIX, Path("managed_whole.md"), b)
        self.assertTrue(region.whole)
        self.assertEqual(region.start, 1)


class CodeRegionTest(unittest.TestCase):
    def test_def_anchor(self):
        r = resolve_code_region(FIX, Path("calc.py"), "def add")
        self.assertFalse(r.whole)
        self.assertIn("return a + b", r.text(FIX))
        self.assertNotIn("scaled_add", r.text(FIX))

    def test_class_anchor(self):
        r = resolve_code_region(FIX, Path("calc.py"), "class Accumulator")
        self.assertIn("def push", r.text(FIX))
        self.assertFalse(r.whole)

    def test_bare_name_anchor(self):
        r = resolve_code_region(FIX, Path("calc.py"), "scaled_add")
        self.assertIn("factor", r.text(FIX))
        self.assertFalse(r.whole)

    def test_unresolved_anchor_degrades_to_whole_file(self):
        r = resolve_code_region(FIX, Path("calc.py"), "def nonexistent")
        self.assertTrue(r.whole)

    def test_non_python_degrades_to_whole_file(self):
        r = resolve_code_region(FIX, Path("managed_add.md"), "def add")
        self.assertTrue(r.whole)

    def test_no_anchor_is_whole_file(self):
        r = resolve_code_region(FIX, Path("calc.py"), None)
        self.assertTrue(r.whole)


class GovernsTest(unittest.TestCase):
    def test_glob_expands(self):
        files = resolve_governed_files(FIX, "*.py")
        self.assertIn(Path("calc.py"), files)

    def test_missing_path_returned_literally(self):
        files = resolve_governed_files(FIX, "nope.py")
        self.assertEqual(files, [Path("nope.py")])


if __name__ == "__main__":
    unittest.main()
