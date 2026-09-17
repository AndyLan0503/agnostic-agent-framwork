"""Mechanisms that hold the framework itself to its own standard (stdlib-only).

AGENTS.md opens the enforcement map with "a rule that exists only in prose is
a wish". These tests are the cooperation-free mechanisms behind rules the
framework states about itself but never checked:

* `PythonFloorTest` - the scaffold must import on a stock macOS Python 3.9.6,
  because `framework/skills/adopt-framework/SKILL.md` tells a new adopter to run
  the suite with whatever `python3` they have.
* `HarnessPermissionsTest` - the shipped allowlist must not auto-approve a
  capability the guardrails reserve for a human, and the deny list must cover
  the secret material guardrail 1 names.
* `RepositoryIdentityTest` - this checkout must be distinguishable from a
  repository that adopted the scaffold, because two rules below apply only to
  one of them.
* `EnforcementMapTest` - every enforcement-map row must cite something that
  exists, defer in a dated shape, or name the adoption step that will fill it
  in. Deferral dates expire here, where someone can act on them, and not in an
  adopted copy that inherited the date.
* `MakeHelpTest` - `make help` must list every documented target.

Every check here reports what it examined and refuses to pass on an empty
scan set (see `framework/knowledge/checks-report-what-they-examined.md`).
"""
from __future__ import annotations

import ast
import datetime
import fnmatch
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent.parent
MAKEFILE = ROOT / "Makefile"
SETTINGS = ROOT / ".claude" / "settings.json"
AGENTS_MD = ROOT / "AGENTS.md"

# Oldest interpreter the scaffold must run on: macOS ships 3.9.6 and nothing
# else. An adopting project may raise its own floor; the framework cannot.
PYTHON_FLOOR = (3, 9)


# --------------------------------------------------------------------------
# Python floor
# --------------------------------------------------------------------------

def script_modules() -> list[Path]:
    return sorted(SCRIPTS.glob("*.py"))


def has_future_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def annotation_nodes(tree: ast.Module):
    """Every expression the interpreter evaluates as an annotation."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                yield node.returns
            args = node.args
            every = (
                list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
                + [a for a in (args.vararg, args.kwarg) if a is not None]
            )
            for arg in every:
                if arg.annotation is not None:
                    yield arg.annotation
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


def pep604_unions(tree: ast.Module) -> list[int]:
    """Line numbers of `X | Y` annotations - a TypeError before 3.10."""
    lines = []
    for annotation in annotation_nodes(tree):
        for node in ast.walk(annotation):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                lines.append(node.lineno)
    return sorted(set(lines))


class PythonFloorTest(unittest.TestCase):
    def test_every_script_parses_at_the_floor(self):
        modules = script_modules()
        self.assertTrue(modules, f"no modules found under {SCRIPTS}")
        for path in modules:
            with self.subTest(module=path.name):
                try:
                    ast.parse(
                        path.read_text(encoding="utf-8"),
                        filename=str(path),
                        feature_version=PYTHON_FLOOR,
                    )
                except SyntaxError as exc:
                    self.fail(
                        f"{path.relative_to(ROOT)} uses syntax newer than Python "
                        f"{PYTHON_FLOOR[0]}.{PYTHON_FLOOR[1]}: {exc}"
                    )

    def test_no_pep604_annotations_without_future_import(self):
        modules = script_modules()
        self.assertTrue(modules, f"no modules found under {SCRIPTS}")
        for path in modules:
            with self.subTest(module=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                if has_future_annotations(tree):
                    continue
                offenders = pep604_unions(tree)
                self.assertEqual(
                    offenders, [],
                    f"{path.relative_to(ROOT)} evaluates PEP 604 `X | Y` annotations "
                    f"at line(s) {offenders} but has no `from __future__ import "
                    f"annotations`. That raises TypeError on Python "
                    f"{PYTHON_FLOOR[0]}.{PYTHON_FLOOR[1]}. Add the future import "
                    f"as the first statement.",
                )


# --------------------------------------------------------------------------
# Framework repository vs. adopted copy
# --------------------------------------------------------------------------

# `framework/scripts/adopt.py` installs the scaffold into a target repo. It
# excludes itself from what it copies, and it writes a `.framework-version`
# into every target recording the framework commit adopted. So a checkout that
# has adopt.py and no `.framework-version` is the framework itself. Both halves
# are required: a project that vendored adopt.py by hand still reads as
# adopted, which is the safe direction to be wrong in.
VERSION_FILE = ".framework-version"


def is_framework_repo(root: Path = ROOT) -> bool:
    return (
        (root / "framework" / "scripts" / "adopt.py").exists()
        and not (root / VERSION_FILE).exists()
    )


class RepositoryIdentityTest(unittest.TestCase):
    """Both branches of the discriminator, on real trees."""

    @staticmethod
    def _tree(tmp: str, adopt_py: bool, version: bool) -> Path:
        root = Path(tmp)
        if adopt_py:
            scripts = root / "framework" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "adopt.py").write_text("", encoding="utf-8")
        if version:
            (root / VERSION_FILE).write_text("deadbeef\n", encoding="utf-8")
        return root

    def test_this_checkout_is_the_framework_repository(self):
        # This module ships verbatim to every adopting repository, where the
        # assertion is false by construction. Guarded the same way
        # `test_no_deferral_in_this_repository_has_expired` is; both branches
        # of the discriminator stay covered by the synthetic trees below, and
        # `test_adoption_smoke.py` fails if this guard is ever dropped.
        if (ROOT / VERSION_FILE).exists():
            self.skipTest(
                f"this repository adopted the scaffold ({VERSION_FILE} is "
                f"present), so it is not the framework repository"
            )
        self.assertTrue(
            is_framework_repo(),
            f"{ROOT} should read as the framework repository: it ships "
            f"framework/scripts/adopt.py and carries no {VERSION_FILE}",
        )

    def test_an_adopted_copy_is_not_the_framework_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp, adopt_py=True, version=True)
            self.assertFalse(
                is_framework_repo(root),
                f"a tree carrying {VERSION_FILE} adopted the scaffold, even if "
                f"it also vendored adopt.py",
            )

    def test_a_tree_without_adopt_py_is_not_the_framework_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(tmp, adopt_py=False, version=False)
            self.assertFalse(is_framework_repo(root))


# --------------------------------------------------------------------------
# Harness permissions
# --------------------------------------------------------------------------

def load_settings() -> dict:
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def rule_parts(rule: str) -> tuple[str, str]:
    """`Bash(git push*)` -> ("Bash", "git push*"); bare tool -> ("Read", "*")."""
    match = re.fullmatch(r"(\w+)\((.*)\)", rule)
    if match:
        return match.group(1), match.group(2)
    return rule, "*"


def rule_matches(rule: str, tool: str, argument: str) -> bool:
    rule_tool, pattern = rule_parts(rule)
    if rule_tool != tool:
        return False
    return fnmatch.fnmatchcase(argument, pattern)


def allow_rules_matching(settings: dict, tool: str, argument: str) -> list[str]:
    return [
        rule for rule in settings["permissions"]["allow"]
        if rule_matches(rule, tool, argument)
    ]


# Capabilities the guardrails reserve for a human (AGENTS.md guardrails 3 and
# 4). None of these may be auto-approved by the shipped allowlist.
HUMAN_ONLY = [
    ("Bash", "git commit -m 'x'"),
    ("Bash", "git push"),
    ("Bash", "git push origin main"),
    ("Bash", "git push --force origin main"),
    ("Bash", "git merge feature"),
    ("Bash", "git tag v1.0.0"),
    ("Bash", "gh pr merge 12"),
    ("Bash", "gh pr merge 12 --squash"),
    ("Bash", "gh pr close 12"),
    ("Bash", "gh pr create --title x --body y"),
    ("Bash", "gh pr edit 12 --add-label ship"),
    ("Bash", "gh issue close 12"),
    ("Bash", "gh issue create --title x"),
    ("Bash", "gh release create v1.0.0"),
    ("Bash", "gh repo delete owner/repo"),
    ("Bash", "gh workflow run deploy.yml"),
    ("Bash", "terraform apply -auto-approve"),
    ("Bash", "make deploy"),
    ("Bash", "make release"),
]


# Secret material guardrail 1 forbids reading into context. Each probe is a
# path such material really lands at; every one must be matched by a deny rule.
# Probes carry a directory component because `fnmatch` treats `**/` as one
# `*` that spans separators - the harness itself also matches the bare name.
SECRET_PATHS = [
    "app/.env",
    "config/.env.production",
    "certs/private.pem",
    "secrets/gcp-serviceaccount.json",
]


def deny_rules_matching(settings: dict, tool: str, argument: str) -> list[str]:
    return [
        rule for rule in settings["permissions"]["deny"]
        if rule_matches(rule, tool, argument)
    ]


def documented_targets() -> list[str]:
    text = MAKEFILE.read_text(encoding="utf-8")
    return re.findall(r"^([A-Za-z0-9_-]+):[^\n]*?## ", text, flags=re.MULTILINE)


def declared_targets() -> set[str]:
    text = MAKEFILE.read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z0-9_-]+):", text, flags=re.MULTILINE)) - {".PHONY"}


def target_recipe(name: str) -> list:
    """The tab-indented lines of one Make target, continuations joined."""
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines()
    recipe, collecting = [], False
    for line in lines:
        if re.match(r"^%s:" % re.escape(name), line):
            collecting = True
            continue
        if collecting:
            if line.startswith("\t"):
                if recipe and recipe[-1].endswith("\\"):
                    recipe[-1] = recipe[-1][:-1] + line.strip()
                else:
                    recipe.append(line.strip())
            elif line.strip():
                break
    return recipe


# `pip`, `pip3` and `python3 -m pip` all resolve to the floor interpreter on
# the stock macOS box the floor targets. Anything needing a newer Python must
# name its own interpreter instead.
FLOOR_PIP = re.compile(
    r"(?:^|[\s;&|(])(?:pip3?|python3?\s+-m\s+pip)\s+install\b"
)


class HarnessPermissionsTest(unittest.TestCase):
    """`.claude/settings.json` is the mechanism behind guardrails 3 and 4.

    Asserts, against the shipped allow/deny lists: (a) nothing in the deny list
    is also reachable through an allow entry, (b) no human-only capability is
    auto-approved, (c) no allow entry is an unbounded tool-wide wildcard, and
    (d) every allowed `make` target actually exists in the Makefile.
    """

    def setUp(self):
        self.settings = load_settings()
        self.allow = self.settings["permissions"]["allow"]
        self.deny = self.settings["permissions"]["deny"]
        self.assertTrue(self.allow, "allow list is empty - nothing to check")
        self.assertTrue(self.deny, "deny list is empty - nothing to check")

    def test_no_allow_entry_reaches_a_denied_capability(self):
        for rule in self.deny:
            tool, pattern = rule_parts(rule)
            # Probe the narrowest and a widened form of each deny pattern.
            probes = {pattern.replace("*", ""), pattern.replace("*", " widened")}
            for probe in probes:
                shadowing = allow_rules_matching(self.settings, tool, probe)
                self.assertEqual(
                    shadowing, [],
                    f"allow entries {shadowing} grant `{tool}({probe})`, which the "
                    f"deny entry `{rule}` forbids",
                )

    def test_human_only_capabilities_are_not_auto_approved(self):
        for tool, argument in HUMAN_ONLY:
            with self.subTest(command=argument):
                matching = allow_rules_matching(self.settings, tool, argument)
                self.assertEqual(
                    matching, [],
                    f"`{argument}` is auto-approved by {matching}. AGENTS.md "
                    f"guardrails 3 and 4 reserve commit/push/merge/deploy for a "
                    f"human, and the enforcement map claims these commands are "
                    f"absent from harness allowlists. Narrow the entry to the "
                    f"read-only subcommands you actually need.",
                )

    def test_secret_paths_are_denied(self):
        self.assertTrue(SECRET_PATHS, "no secret probes - nothing examined")
        for path in SECRET_PATHS:
            with self.subTest(path=path):
                matching = deny_rules_matching(self.settings, "Read", path)
                self.assertTrue(
                    matching,
                    f"nothing in the deny list stops `Read({path})`. AGENTS.md "
                    f"guardrail 1 forbids reading secret material into context "
                    f"and the enforcement map cites this file as the mechanism.",
                )

    def test_no_allow_entry_is_a_tool_wide_wildcard(self):
        for rule in self.allow:
            tool, pattern = rule_parts(rule)
            self.assertNotIn(
                pattern.strip(), ("*", ""),
                f"`{rule}` auto-approves every use of {tool}",
            )

    def test_allowed_make_targets_exist(self):
        declared = declared_targets()
        allowed = [
            pattern for rule in self.allow
            for tool, pattern in [rule_parts(rule)]
            if tool == "Bash" and pattern.startswith("make ")
        ]
        self.assertTrue(allowed, "no `make` target is allowed - expected at least one")
        for pattern in allowed:
            target = pattern[len("make "):].strip()
            self.assertNotIn(
                "*", target,
                f"`Bash({pattern})` allows any target; `make` runs whatever the "
                f"working tree's Makefile says, and the Makefile is editable. "
                f"List the named targets instead.",
            )
            self.assertIn(
                target, declared,
                f"`Bash({pattern})` allows a target that the Makefile does not define",
            )


# --------------------------------------------------------------------------
# Enforcement map
# --------------------------------------------------------------------------

# A row defers its mechanism in exactly this shape. The date is when the row
# must be honoured by - a deferral without one is a wish with extra steps.
DEFERRAL = re.compile(r"<fill in by (\d{4}-\d{2}-\d{2}): [^>]+>")
DEFERRAL_SHAPE = "<fill in by YYYY-MM-DD: what will back this rule>"

# Rows exempted from needing a mechanism, by name, with the reason. Burned down
# to empty on 2026-09-14: every shipped row now cites a path, defers with a
# date, or is marked `Adopter-owned` and names the adoption step. The test below
# deletes an entry that stops being true, so the list cannot rot silently, and
# it can only grow by someone editing this file and saying why.
PENDING_CITATION: dict = {}

# Rows only the adopting project can defend. The marker is not a way to say
# nothing: a row carrying it must name the adoption step that fills it in.
ADOPTER_OWNED = "adopter-owned"
ADOPTION_SKILL = "framework/skills/adopt-framework/SKILL.md"

# The scaffold ships twelve rows. A parse that finds fewer than this is the
# table drifting out of the shape the reader below expects, not a project
# pruning rows.
MIN_ROWS = 10

_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"\b(?:https?://|[\w-]+\.(?:com|org|io|net|dev)/)\S+")
_PATH = re.compile(r"(?<![\w./-])((?:[\w.-]+/)+[\w.-]+)")
_MAKE = re.compile(r"`make ([a-z0-9_-]+)`")


def enforcement_rows() -> list[tuple[str, str]]:
    """(limit, mechanism) for every row of the AGENTS.md enforcement map."""
    text = AGENTS_MD.read_text(encoding="utf-8")
    section = re.search(
        r"^## Enforcement map\s*$(.*?)(?=^## )", text, flags=re.M | re.S
    )
    if section is None:
        return []
    rows = []
    seen_header = False
    for line in section.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not seen_header:
            if cells[:2] == ["Limit", "Mechanism"]:
                seen_header = True
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if len(cells) >= 2:
            rows.append((cells[0], cells[1]))
    return rows


def _top_level_names() -> set[str]:
    return {p.name for p in ROOT.iterdir()}


def path_tokens(cell: str) -> list[str]:
    """Repository paths a row claims, ignoring URLs and prose like `remote/external`.

    A slashed token counts as a path claim when it carries a file extension or
    starts at a real top-level entry of the repository.
    """
    cleaned = _MD_LINK.sub(r"\1", cell)
    cleaned = _URL.sub(" ", cleaned)
    cleaned = cleaned.replace("`", " ")
    top = _top_level_names()
    tokens = []
    for raw in _PATH.findall(cleaned):
        token = raw.rstrip("/.,;")
        head, _, tail = token.partition("/")
        if head in top or re.search(r"\.[A-Za-z0-9]{1,5}$", tail):
            tokens.append(token)
    return tokens


def expired_deferrals(
    rows: "list[tuple[str, str]]", today: datetime.date
) -> "list[tuple[str, str]]":
    """(limit, date) for every deferral whose date has already passed.

    A date that is not a calendar date is skipped here - reporting it is
    `test_deferrals_use_the_dated_shape`'s job, and one defect should not be
    reported twice in different words.
    """
    out = []
    for limit, mechanism in rows:
        for date in DEFERRAL.findall(mechanism):
            try:
                due = datetime.date.fromisoformat(date)
            except ValueError:
                continue
            if due < today:
                out.append((limit, date))
    return out


def expiry_failures(
    rows: "list[tuple[str, str]]", today: datetime.date, framework_repo: bool
) -> "list[tuple[str, str]]":
    """Expired deferrals that this repository is answerable for.

    A deadline is only a mechanism where somebody can act on it. In the
    framework repository a passed date is a real failure. In a repository that
    adopted the scaffold the date was inherited, not chosen, and going red on
    it would teach the team to disable the check - so there it reports nothing
    until the adopter sets dates of its own.
    """
    return expired_deferrals(rows, today) if framework_repo else []


class EnforcementMapTest(unittest.TestCase):
    """The framework's own standard, applied to the table that states it.

    A row is backed when it cites something real - a repository path or a
    Makefile target - or defers in the dated shape above. A row that names a
    script which does not exist fails here rather than in a reader's head.
    """

    def setUp(self):
        self.rows = enforcement_rows()

    def test_table_parses(self):
        # Guards against the check quietly examining nothing if the table drifts.
        self.assertGreaterEqual(
            len(self.rows), MIN_ROWS,
            f"parsed only {len(self.rows)} enforcement-map rows from "
            f"{AGENTS_MD.name}; the table format under `## Enforcement map` "
            f"must stay a markdown table headed `| Limit | Mechanism |`",
        )

    def test_cited_paths_exist(self):
        for limit, mechanism in self.rows:
            for token in path_tokens(mechanism):
                with self.subTest(row=limit, path=token):
                    self.assertTrue(
                        (ROOT / token).exists(),
                        f"enforcement-map row {limit!r} cites {token!r}, which does "
                        f"not exist in the repository",
                    )

    def test_cited_make_targets_exist(self):
        declared = declared_targets()
        for limit, mechanism in self.rows:
            for target in _MAKE.findall(mechanism):
                with self.subTest(row=limit, target=target):
                    self.assertIn(
                        target, declared,
                        f"enforcement-map row {limit!r} cites `make {target}`, which "
                        f"the Makefile does not define",
                    )

    def test_deferrals_use_the_dated_shape(self):
        for limit, mechanism in self.rows:
            for date in DEFERRAL.findall(mechanism):
                with self.subTest(row=limit, date=date):
                    try:
                        datetime.date.fromisoformat(date)
                    except ValueError:
                        self.fail(
                            f"enforcement-map row {limit!r} defers to {date!r}, which "
                            f"is not a calendar date. Use {DEFERRAL_SHAPE}."
                        )

    def test_expiry_is_computed_from_the_date(self):
        rows = [
            ("Past", "`<fill in by 2020-01-01: a deadline that passed>`"),
            ("Future", "`<fill in by 2999-12-31: a deadline that has not>`"),
            ("Malformed", "`<fill in by 2026-02-30: not a calendar date>`"),
            ("Backed", "`framework/scripts/gnhf_guard.py`"),
        ]
        today = datetime.date(2026, 9, 14)
        self.assertEqual(
            expired_deferrals(rows, today), [("Past", "2020-01-01")]
        )

    def test_expiry_does_not_fail_an_adopted_copy(self):
        rows = [("Past", "`<fill in by 2020-01-01: inherited deadline>`")]
        today = datetime.date(2026, 9, 14)
        self.assertEqual(
            expiry_failures(rows, today, framework_repo=False), [],
            "an adopted copy must not go red on a date the framework chose",
        )
        self.assertEqual(
            expiry_failures(rows, today, framework_repo=True),
            [("Past", "2020-01-01")],
            "the framework repository must go red on its own passed date",
        )

    def test_no_deferral_in_this_repository_has_expired(self):
        framework_repo = is_framework_repo()
        if not framework_repo:
            self.skipTest(
                "this repository adopted the scaffold; deferral dates it "
                "inherited are not its to answer for (CONTRIBUTING.md, "
                "'Adding an enforcement-map row')"
            )
        overdue = expiry_failures(
            self.rows, datetime.date.today(), framework_repo
        )
        self.assertEqual(
            overdue, [],
            f"enforcement-map deferral(s) {overdue} are past their date. Back "
            f"the row with a real mechanism, or move the date and say in the "
            f"commit message why it slipped. A deferral nobody honours is the "
            f"wish the table exists to forbid.",
        )

    def test_adopter_owned_rows_name_the_adoption_step(self):
        # Zero marked rows is a legitimate result: an adopted project that has
        # filled its rows in has none left. What must never happen is a row
        # claiming `Adopter-owned` and naming no step to do it at.
        marked = [
            (limit, mechanism) for limit, mechanism in self.rows
            if ADOPTER_OWNED in mechanism.lower()
        ]
        for limit, mechanism in marked:
            with self.subTest(row=limit):
                self.assertIn(
                    ADOPTION_SKILL, mechanism,
                    f"enforcement-map row {limit!r} is marked Adopter-owned but "
                    f"names no adoption step. Cite {ADOPTION_SKILL} and the step "
                    f"number that fills the row in, so the deferral has an "
                    f"owner and a place.",
                )

    def test_every_row_is_backed_or_dated(self):
        unbacked = []
        backed = []
        for limit, mechanism in self.rows:
            has_path = any((ROOT / t).exists() for t in path_tokens(mechanism))
            has_target = any(t in declared_targets() for t in _MAKE.findall(mechanism))
            has_deferral = bool(DEFERRAL.search(mechanism))
            if has_path or has_target or has_deferral:
                backed.append(limit)
            else:
                unbacked.append(limit)

        self.assertTrue(backed, "no enforcement-map row is backed by anything")

        # The pending list burns down: an entry that no longer names an
        # unbacked row must be deleted, so it cannot linger as dead weight.
        stale = sorted(set(PENDING_CITATION) - set(unbacked))
        self.assertEqual(
            stale, [],
            f"PENDING_CITATION names {stale}, which no longer need it - the "
            f"row(s) are either backed now or gone from the map. Delete those "
            f"entries from this test.",
        )

        still_unbacked = sorted(set(unbacked) - set(PENDING_CITATION))
        self.assertEqual(
            still_unbacked, [],
            f"enforcement-map row(s) {still_unbacked} state a limit without a "
            f"mechanism anyone can check. Each row's Mechanism cell must contain "
            f"at least one of: a repository path that exists, a `make <target>` "
            f"the Makefile defines, or a dated deferral in the shape "
            f"{DEFERRAL_SHAPE}.",
        )


# --------------------------------------------------------------------------
# make help
# --------------------------------------------------------------------------

class MakeHelpTest(unittest.TestCase):
    def test_help_lists_every_documented_target(self):
        targets = documented_targets()
        self.assertTrue(targets, "no `## `-documented targets found in the Makefile")
        result = subprocess.run(
            ["make", "help"], cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = re.findall(r"^\s+([A-Za-z0-9_-]+)\s", result.stdout, flags=re.MULTILINE)
        missing = sorted(set(targets) - set(listed))
        self.assertEqual(
            missing, [],
            f"`make help` omits documented target(s) {missing}. Output was:\n"
            f"{result.stdout}",
        )


class SetupInterpreterTest(unittest.TestCase):
    """`make setup` must not install knowform with the Python 3.9 floor.

    knowform requires >= 3.10 and the suites deliberately run on the stock
    macOS 3.9 (AGENTS.md "Conventions"). Shipped as `pip install`, `make setup`
    could not run at all on the interpreter the rest of the repository targets.
    """

    def test_setup_does_not_install_knowform_with_the_floor_interpreter(self):
        recipe = target_recipe("setup")
        self.assertTrue(recipe, "the `setup` target has an empty recipe")
        if not any("knowform" in line for line in recipe):
            self.skipTest(
                "this repository's `setup` does not install knowform; the "
                "version conflict this guards is not present"
            )
        offenders = [line for line in recipe if FLOOR_PIP.search(line)]
        self.assertEqual(
            offenders, [],
            f"`make setup` installs knowform with the floor interpreter: "
            f"{offenders}. knowform needs Python >= 3.10, the floor is "
            f"{PYTHON_FLOOR[0]}.{PYTHON_FLOOR[1]}, and bare `pip` is not even "
            f"on PATH on a stock macOS box. Name a newer interpreter - see the "
            f"`TOOLS_PYTHON` / `TOOLS_VENV` pattern in the Makefile.",
        )
        print(f"setup recipe: {len(recipe)} line(s) checked")

    def test_reconcile_runs_the_knowform_that_setup_installed(self):
        recipe = target_recipe("reconcile")
        self.assertTrue(recipe, "the `reconcile` target has an empty recipe")
        if not any("knowform" in line for line in recipe):
            self.skipTest("this repository's `reconcile` does not run knowform")
        venv = [line for line in target_recipe("setup") if "-m venv" in line]
        if not venv:
            self.skipTest("`setup` installs knowform outside a venv")
        self.assertTrue(
            any("$(TOOLS_VENV)" in line for line in recipe),
            f"`make setup` installs knowform into $(TOOLS_VENV) but "
            f"`make reconcile` calls a knowform from PATH: {recipe}. That is "
            f"either a different version or nothing at all.",
        )


if __name__ == "__main__":
    unittest.main()
