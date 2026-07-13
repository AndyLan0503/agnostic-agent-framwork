import tempfile
import unittest
from pathlib import Path

from reconcile.graph import DocNode, build_graph, frontier
from reconcile.regions import Region

FIX = Path(__file__).parent / "fixtures"


class GraphTest(unittest.TestCase):
    def test_calls_edge_extracted(self):
        graph = build_graph(FIX, [], {Path("calc.py")})
        # scaled_add and Accumulator.push both CALL add.
        callers = {src for src, dsts in graph.edges.items()
                   if "calc.py::add" in dsts}
        self.assertIn("calc.py::scaled_add", callers)

    def test_reachable_bounded_by_depth(self):
        graph = build_graph(FIX, [], {Path("calc.py")})
        seed = {"calc.py::scaled_add"}
        # add is one CALLS hop away.
        self.assertIn("calc.py::add", graph.reachable(seed, 1))
        self.assertNotIn("calc.py::add", graph.reachable(seed, 0))

    def test_governs_maps_doc_to_symbol(self):
        add_region = Region(Path("calc.py"), 4, 5)  # def add span
        doc = DocNode(key="d#add", region=add_region)
        graph = build_graph(FIX, [doc], {Path("calc.py")})
        self.assertEqual(graph.governs["d#add"], "calc.py::add")

    def test_frontier_follows_governs_backward(self):
        add_region = Region(Path("calc.py"), 4, 5)
        doc = DocNode(key="d#add", region=add_region)
        graph = build_graph(FIX, [doc], {Path("calc.py")})
        # Changing scaled_add reaches add (depth 1) -> the governed doc.
        reached = frontier(graph, {"calc.py::scaled_add"}, depth=1)
        self.assertIn("d#add", reached)

    def test_graph_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "m.py").write_text("def f():\n    return 1\n")
            before = {p.name for p in root.iterdir()}
            build_graph(root, [], {Path("m.py")})
            self.assertEqual({p.name for p in root.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
