"""PreToolUse guard for unattended (gnhf) runs.

Blocks writes outside the repository, reads of secret material, remote git
actions, network commands and web tools. Hooks run on every tool call
regardless of permission mode, so this holds even with prompts bypassed.
Defense, not proof: for a hard guarantee, run the whole session
network-isolated.

Two of those cover a tool boundary the harness config cannot reach. The
`Edit`/`Write`/`NotebookEdit` branch has always confined the edit tools to the
repository, but a shell redirection creates a file too, and `_segments` drops
redirect targets so that nothing looked at them: `echo pwned > /tmp/outside`
was an unconfined write the enforcement map already claimed was impossible.
`_writes_outside` resolves every redirect target against the invocation's cwd
and refuses one that lands outside, refusing `~` and `$` targets it cannot
resolve rather than guessing. A write carried in a command's own arguments
(`cp`, `tee`, `dd of=`) is still outside what this can reach. Likewise the
`Read(**/.env)` deny rules in `.claude/settings.json` bind one tool, and Bash
is the other way to put a file in front of the model, so `_reads_secret`
enforces the same names against every token of a command.

Commands are split on newlines, tokenised with `shlex`, split into segments
at shell operators, and judged on each segment's command word and its own
arguments. That is what makes `cat android/gradle.properties` and
`grep -rn 'npm install' README.md` routine reads rather than false positives,
while `cd apps && pnpm install`, `(pnpm install)` and `PATH=/x pnpm install`
stay blocked. Over-blocking is a security defect by another route: a guard
that stops routine reads is a guard somebody switches off.

`shlex` is not bash, and the gap between the two is where the bypasses live,
so the guard fails closed wherever it cannot resolve what the shell will run.
The command word is the sharp edge, and it is judged by an allowlist: bash
performs eight expansion classes on a word, a denylist of metacharacters
covered three of them, and the others - brace expansion, globbing, tilde
expansion - each resolved to a command the guard never saw and therefore
allowed. Only a word made of plain name and path characters is classified;
`curl${IFS}x`, `$CMD x`, `cur{l,l} x`, `cur[l] x` and `~/bin/curl x` are all
refused instead. Alongside that: a command `shlex` cannot tokenise, a command
past _MAX_COMMAND_LENGTH, a shell or interpreter with no script the guard can
read, a package-manager subcommand that is not on the local list, a wrapper
whose target cannot be found, and nesting past _MAX_DEPTH are blocked rather
than allowed. `main` returns 2 - the only exit code a PreToolUse hook treats
as blocking - on every unexpected exception, so a crash denies.

Known residual holes, carried honestly rather than papered over. Anything the
run can *write* and then execute through an allowed invocation (`make test`,
`python3 -m unittest`, `node script.js`) is outside what command-line pattern
matching can close, and so are interpreters that take code in an argument the
guard does not model - `awk 'BEGIN{system("curl ...")}'`, `find . -exec curl
{} \\;`, `vim -c '!curl ...'` - and build tools that resolve dependencies
remotely with no distinguishing subcommand (`cargo`, `go`, `mvn`, `dotnet`).

Several of the tables are enumerations, and an enumeration is always one name
behind the world. Each of these was checked and is open: a shell missing from
SHELL_RUNNERS (`ion -c`, `murex -c`, `ksh88 -c`), a wrapper missing from
ARG_WRAPPERS (`valgrind curl`, `mpirun curl`, `srun curl`, `qemu-x86_64
curl`), and a package manager missing from BLOCKED_SUBCOMMANDS (`conan
install`, `composer install`, `cpanm`, `apt-get install`, `apk add`,
`nix-shell -p`, `stack build`, `mix deps.get`). `make -f evil.mk` belongs to
the write-then-execute class above.

`docker run <image> curl ...` was open for a different reason - `docker` is
modelled by subcommand and `run` executed a command word nothing classified -
and is now resolved past the image, the way `timeout` is resolved past its
duration (EXEC_WRAPPERS). `docker compose` is not: `docker compose run svc
curl ...` and a compose file the run wrote itself both execute through it,
`docker start` replays a container created before the rule existed, and the
standalone `docker-compose` binary is not modelled at all.

ARG_WRAPPERS has a second weakness beyond being a list: finding a wrapper's
target is a heuristic. An operand that follows a flag counts as the command
only when the guard already knows the name, so a wrapper flag that takes a
separate value can still shadow a command the guard does not know. Closing any
of this needs network isolation, not another rule.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import sys
from pathlib import Path

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
NETWORK_TOOLS = {"WebFetch", "WebSearch"}

# Local-only subcommands of otherwise-blocked tools. Criterion for adding
# one: fully local - no network, no remote mutation, no secret reads, and
# no flag can introduce a remote source (which is why `helm template` and
# `terraform plan` are absent). Chaining cannot ride through, because each
# segment of a compound command is classified on its own.
SAFE_BASH = {
    "terraform": {"fmt", "validate", "version"},
    "helm": {"lint", "version"},
    "twine": {"check"},
}

# Tool families with no local subcommand worth keeping. An entry for a stack
# an adopting project does not use costs nothing - the binary is not on PATH
# and the rule never fires - while a missing family is a bypass, so this errs
# towards covering stacks the scaffold itself does not ship. Adopting projects
# extend it; trimming it only ever loosens the guard.
BLOCKED_COMMANDS = {
    "gh": "GitHub CLI",
    "gcloud": "cloud and infra CLIs",
    "aws": "cloud and infra CLIs",
    "az": "cloud and infra CLIs",
    "kubectl": "cloud and infra CLIs",
    "helm": "cloud and infra CLIs",
    "terraform": "cloud and infra CLIs",
    "curl": "network commands",
    "wget": "network commands",
    "ssh": "network commands",
    "scp": "network commands",
    "rsync": "network commands",
    "nc": "network commands",
    "ncat": "network commands",
    "socat": "network commands",
    "telnet": "network commands",
    "ftp": "network commands",
    "sftp": "network commands",
    "http": "HTTPie",
    "https": "HTTPie",
    "httpie": "HTTPie",
    "open": "opens URLs and applications outside the session",
    "osascript": "AppleScript can shell out past every other rule",
    "twine": "package publishing",
    "npx": "remote package execution",
    "pnpx": "remote package execution",
    "bunx": "remote package execution",
    "uvx": "remote package execution",
    "corepack": "downloads package manager releases",
    "deno": "resolves and runs remote modules",
    "pod": "CocoaPods (fetches the spec repo and pods)",
    "gradle": "Gradle (resolves dependencies remotely)",
    "gradlew": "Gradle (resolves dependencies remotely)",
    "xcodebuild": "xcodebuild (resolves Swift packages remotely)",
    "brew": "Homebrew",
    "eas": "Expo Application Services (remote builds)",
}

# Families kept usable: only the subcommands that reach out are blocked.
BLOCKED_SUBCOMMANDS = {
    "docker": ({"push", "login"}, "registry writes"),
    "podman": ({"push", "login"}, "registry writes"),
    "expo": (
        {
            "export",
            "install",
            "login",
            "logout",
            "prebuild",
            "publish",
            "register",
            "upload",
            "whoami",
        },
        "Expo network operations",
    ),
    "maestro": ({"cloud", "login", "logout"}, "Maestro Cloud"),
    # `busybox` is not here: it multiplexes, so it is an ARG_WRAPPERS entry and
    # every applet - not the five somebody enumerated - is classified on its
    # own name. `busybox sh -c 'curl x'` reached all of them and everything on
    # PATH besides.
    "gem": ({"install", "update", "fetch", "push"}, "RubyGems"),
    "bundle": ({"install", "update", "add"}, "Bundler"),
    "swift": ({"package"}, "Swift Package Manager (resolves remotely)"),
    "pip": ({"install", "download", "wheel"}, "package installation"),
    "pip3": ({"install", "download", "wheel"}, "package installation"),
    # Python packaging past `pip`. `uv` does the job `pip` used to, and
    # `poetry`/`pipenv` were already modelled well enough for the guard to
    # follow their `run` (EXEC_WRAPPERS) while their `install` went unread.
    "uv": (
        {
            "add",
            "build",
            "export",
            "init",
            "lock",
            "publish",
            "python",
            "remove",
            "self",
            "sync",
            "tool",
            "venv",
        },
        "uv (Python packaging)",
    ),
    "poetry": (
        {
            "add",
            "export",
            "init",
            "install",
            "lock",
            "new",
            "publish",
            "remove",
            "search",
            "self",
            "source",
            "sync",
            "update",
        },
        "Poetry (Python packaging)",
    ),
    "pipenv": (
        {"install", "lock", "sync", "uninstall", "update", "upgrade"},
        "Pipenv (Python packaging)",
    ),
    "pdm": (
        {
            "add",
            "import",
            "init",
            "install",
            "lock",
            "publish",
            "remove",
            "self",
            "sync",
            "update",
        },
        "PDM (Python packaging)",
    ),
    "conda": (
        {
            "create",
            "env",
            "init",
            "install",
            "remove",
            "search",
            "uninstall",
            "update",
            "upgrade",
        },
        "conda (Python packaging)",
    ),
    "mamba": (
        {"create", "env", "init", "install", "remove", "search", "uninstall", "update", "upgrade"},
        "conda (Python packaging)",
    ),
    "micromamba": (
        {"create", "env", "init", "install", "remove", "search", "uninstall", "update", "upgrade"},
        "conda (Python packaging)",
    ),
    "rye": (
        {"add", "fetch", "init", "install", "lock", "publish", "remove", "sync", "toolchain"},
        "Rye (Python packaging)",
    ),
    "hatch": (
        {"build", "dep", "env", "new", "publish"},
        "Hatch (Python packaging)",
    ),
    "pixi": (
        {"add", "init", "install", "remove", "search", "update", "upgrade"},
        "pixi (Python packaging)",
    ),
    # `make test` is the pipeline's gate and stays allowed; `make setup`
    # installs the toolchain from the network.
    "make": ({"setup"}, "make setup installs the toolchain from the network"),
}

PACKAGE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
PM_NETWORK_SUBCOMMANDS = {
    "add",
    "audit",
    "ci",
    "create",
    "dedupe",
    "deploy",
    "dlx",
    "fund",
    "i",
    "import",
    "info",
    "init",
    "install",
    "link",
    "outdated",
    "pack",
    "patch",
    "publish",
    "remove",
    "rm",
    "search",
    "un",
    "uninstall",
    "unlink",
    "up",
    "update",
    "upgrade",
    "view",
    "x",
}
# The local list is the allowlist: anything not on it counts as
# network-capable. Enumerating the reaching-out half does not work - npm alone
# accepts `in`, `ins`, `inst`, `isnt`, `isntall`, `clean-install` and
# `install-ci-test` for one operation. Recognising the local subcommands is
# what keeps `npm run ci` and `pnpm run install-hooks` working: the scan stops
# at `run`.
PM_LOCAL_SUBCOMMANDS = {
    "bin",
    "config",
    "exec",
    "explain",
    "help",
    "licenses",
    "list",
    "ll",
    "ls",
    "prefix",
    "rebuild",
    "root",
    "run",
    "run-script",
    "start",
    "store",
    "test",
    "version",
    "why",
}
# Flags that answer without running anything, so a bare invocation with one of
# them is not the `yarn`-installs-by-default shape.
PM_INFO_FLAGS = {"-v", "--version", "-h", "--help"}
# Flags that swallow the next token, so it is not the subcommand.
PM_VALUE_FLAGS = {
    "-C",
    "-F",
    "-w",
    "--cache",
    "--cwd",
    "--dir",
    "--filter",
    "--loglevel",
    "--prefix",
    "--registry",
    "--reporter",
    "--scope",
    "--store-dir",
    "--userconfig",
    "--workspace",
}

GIT_BLOCKED_SUBCOMMANDS = {
    "push",
    "pull",
    "fetch",
    # The plumbing `push` and `fetch` themselves call. Naming only the
    # porcelain leaves `git send-pack origin main` - a push - allowed.
    "send-pack",
    "fetch-pack",
    "clone",
    "daemon",
    "ls-remote",
    "submodule",
    "request-pull",
    "send-email",
    "svn",
    # `git p4` syncs with a Perforce depot, a remote the same way `svn` is.
    "p4",
}
# `git -c KEY=VALUE` where KEY names a program git will run: `git -c
# core.pager='curl x' log` executes the value, and the guard already parsed
# `-c` well enough to step over it and no further. Allowlisted the same way
# the command word is - the settings that cannot name a program are short and
# knowable, the ones that can are not (`alias.*`, `filter.*.clean`,
# `*.textconv`, `credential.helper`, `diff.external`, ...).
GIT_SETTINGS_THAT_NAME_NO_PROGRAM = {
    "advice.detachedhead",
    "color.ui",
    "commit.gpgsign",
    "core.autocrlf",
    "core.filemode",
    "protocol.version",
    "push.default",
    "user.email",
    "user.name",
}
GIT_VALUE_FLAGS = {
    "-C",
    "-c",
    "--config-env",
    "--exec-path",
    "--git-dir",
    "--namespace",
    "--work-tree",
}

# `node -e` / `python3 -c` run arbitrary code, which voids every other rule.
NODE_EVAL_FLAGS = {"-e", "--eval", "-p", "--print", "-r", "--require", "--input-type"}
NODE_EVAL_SHORT = {"e", "p", "r"}
PYTHON_MODULE_BLOCKED = {"pip", "http.server", "ensurepip", "venv"}
# Python flags that consume the token after them, so what follows is a value
# and not the script path.
PYTHON_VALUE_LETTERS = {"W", "X"}
PYTHON_VALUE_LONG_FLAGS = {"--check-hash-based-pycs"}
# Same shape in the neighbouring interpreters. Letters, not whole flags, so a
# cluster (`perl -we`) is caught the way `node -pe` already was.
INLINE_EVAL_LETTERS = {
    "ruby": {"e"},
    "perl": {"e", "E"},
    "php": {"r"},
}
# Flags that make an interpreter print something and exit, so the invocation
# is not a stdin read. The counterweight to the stdin rule below: a guard that
# blocks `node --version` is a guard somebody switches off.
NODE_INFO_FLAGS = {"-v", "--version", "-h", "--help"}
PYTHON_INFO_FLAGS = {"-V", "--version", "-h", "--help"}
# The same, for anything else that would otherwise be judged on what it might
# go on to run: `python3 -m venv --help` installs nothing, `busybox --help`
# multiplexes nothing and `bash --version` reads no script. Deliberately not
# `-v`, which is verbose mode to bash and to python, not a version request.
INFO_FLAGS = {"-h", "--help", "-V", "--version"}
# Interpreters that run whatever arrives on stdin when the command line names
# no script: `echo 'system("curl x")' | ruby` runs it. `python` and `node`
# have their own flag grammars below; these three need only their exit flags.
STDIN_INTERPRETERS = {
    "ruby": {"-v", "--version", "-h", "--help"},
    "perl": {"-v", "-V", "-h", "--help"},
    "php": {"-v", "--version", "-h", "--help", "-i", "-m"},
}

# Prefixes that pass their tail on to another command. The value is how many
# operands the wrapper takes for itself before that command - `timeout` a
# duration, `flock` a lock file, `chroot` a directory - which is what made
# `timeout 30 curl x` read as a command named `30`. `timeout` is what an agent
# reaches for when something might hang, so the shape gets hit by accident as
# well as deliberately.
ARG_WRAPPERS = {
    "busybox": 0,  # a multiplexer: `busybox sh` reaches every applet and PATH
    "chroot": 1,
    "chrt": 0,
    "command": 0,
    "daemonize": 0,
    "doas": 0,
    "firejail": 0,
    "env": 0,
    "exec": 0,
    "flock": 1,
    "ionice": 0,
    "ltrace": 0,
    "nice": 0,
    "nohup": 0,
    "parallel": 0,
    "proot": 0,
    "setarch": 1,
    "setsid": 0,
    "stdbuf": 0,
    "systemd-run": 0,
    "strace": 0,
    "sudo": 0,
    "taskset": 1,
    "time": 0,
    "timeout": 1,
    "unbuffer": 0,
    "watch": 0,
    "xargs": 0,
}
# The same idea one token in: a (command, subcommand) pair that runs the rest
# as another command. The value is ARG_WRAPPERS' value - how many operands the
# pair takes for itself before that command. `poetry run` takes none;
# `docker run` takes the image and `docker exec` the container, which is why
# `docker run --rm alpine curl https://evil.tld` used to read as a `docker`
# invocation whose only classified word was `run`. `docker create` does not
# execute, but it records the command `docker start` later runs, so leaving it
# out only splits the same bypass across two allowed calls.
EXEC_WRAPPERS = {
    ("bundle", "exec"): 0,
    ("conda", "run"): 0,
    ("docker", "create"): 1,
    ("docker", "exec"): 1,
    ("docker", "run"): 1,
    ("hatch", "run"): 0,
    ("mamba", "run"): 0,
    ("micromamba", "run"): 0,
    ("pdm", "run"): 0,
    ("pipenv", "run"): 0,
    ("pixi", "run"): 0,
    ("podman", "create"): 1,
    ("podman", "exec"): 1,
    ("podman", "run"): 1,
    ("poetry", "run"): 0,
    ("rye", "run"): 0,
    ("uv", "run"): 0,
}
# `docker container run` is `docker run` with the management command spelled
# out, and both CLIs accept either. Modelling only the short spelling leaves
# the bypass one word away, so the management word is dropped first.
CONTAINER_ALIASES = {("docker", "container"), ("podman", "container")}
# A prefix that re-spells its tail as another tool: `uv pip install` is
# `pip install`, and `uv` must not get a looser rule than the tool it fronts.
ALIAS_WRAPPERS = {("uv", "pip"): "pip"}
# Every shell that takes its script in a `-c` argument, plus `su` and
# `runuser`, which hand one to the user's login shell and never re-parse it.
# Five names covered the shells somebody thought of; the rest walked past.
SHELL_RUNNERS = {
    "ash",
    "bash",
    "csh",
    "dash",
    "elvish",
    "fish",
    "ksh",
    "ksh93",
    "mksh",
    "pdksh",
    "rbash",
    "runuser",
    "nu",
    "osh",
    "sh",
    "su",
    "tcsh",
    "xonsh",
    "yash",
    "zsh",
}
# Keywords that can open a segment; the real command word follows them. `[`
# and `[[` are here for the same reason: they take a condition, never another
# command, and an allowlisted command word would otherwise refuse them.
SHELL_KEYWORDS = {
    "!",
    "[",
    "[[",
    "]]",
    "do",
    "done",
    "elif",
    "else",
    "esac",
    "fi",
    "for",
    "if",
    "in",
    "then",
    "until",
    "while",
    "{",
    "}",
}
# Keywords that introduce a *definition*, where the word after them names the
# construct rather than the command. `function` used to be stripped as an
# ordinary keyword, which promoted the function name to the command word and
# demoted the body to its arguments: `function f { curl x; }; f` ran unseen.
# The name is dropped only when a `{` follows it, so `coproc curl x` - where
# the command word comes straight after - still resolves to `curl`.
SHELL_DEFINITION_KEYWORDS = {"coproc", "function"}
# `.` and `source` hand the current shell a script the guard never sees, which
# is what `sh payload.sh` was already blocked for - and they run it in the
# current shell, so every later rule is off too.
SCRIPT_SOURCERS = {".", "source"}

KNOWN_COMMANDS = (
    set(BLOCKED_COMMANDS)
    | set(BLOCKED_SUBCOMMANDS)
    | set(SAFE_BASH)
    | set(ARG_WRAPPERS)
    | set(INLINE_EVAL_LETTERS)
    | set(STDIN_INTERPRETERS)
    | PACKAGE_MANAGERS
    | SHELL_RUNNERS
    | {"git", "node", "nodejs", "python", "python3", "eval"}
)

_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PUNCTUATION = re.compile(r"^[();<>|&]+$")
_SHORT_FLAG_CLUSTER = re.compile(r"^-[A-Za-z]+$")
# Every spelling of the interpreter, not just `python3`: an adopting project
# may pin a versioned one, and `python3.13 -c` used to walk straight past the
# inline-eval and pip rules that `python3 -c` hits. The trailing `t` is
# CPython's free-threaded build (`python3.13t`, what `uv python install 3.13t`
# and the python.org installer produce), the `w` is macOS/Windows `pythonw`,
# and `pypy` evaluates `-c` the same way - each of them is an unrestricted
# interpreter to anything that finds one on PATH.
_PYTHON_COMMAND = re.compile(r"^(?:python|pypy)w?(?:\d+(?:\.\d+)*)?t?$")
# The shape of a command word the guard is willing to classify: plain
# identifier and path characters, nothing else. An allowlist, not a denylist of
# metacharacters, because bash performs eight expansion classes on a word and
# a denylist covered three of them - `curl${IFS}x` was refused while
# `cur{l,l}`, `cur[l]` and `~/bin/curl` read as unknown commands and ran. One
# rule closes the classes nobody has enumerated yet along with the ones they
# have; the cost is that an exotic but genuine command word is refused too,
# which is the direction this guard is supposed to fail in.
_RESOLVED_COMMAND_WORD = re.compile(r"^[A-Za-z0-9_.+@/-]+$")
# Wrapper, `sh -c` and `eval` nesting all recurse; past this the guard stops
# resolving, so it stops allowing.
_MAX_DEPTH = 8
# `shlex` costs about n^1.8 - 200 KB takes 0.4 s and 2 MB takes 25 s - so a few
# megabytes of padding runs past the 60 s PreToolUse default, and a hook that
# times out is a *non-blocking* error, which runs the command. Well past any
# real command; everything above this is padding.
_MAX_COMMAND_LENGTH = 16384
# bash opens a socket for a redirection to /dev/tcp/host/port (and /dev/udp),
# which is a network command with no command word at all:
# `exec 3<>/dev/tcp/evil/80`. Special only as a redirect target, so
# `grep -rn /dev/tcp notes.md` stays a routine read.
_NETWORK_DEVICE = re.compile(r"^/dev/(?:tcp|udp)/")
_NESTED_TOO_DEEP = "blocked in unattended runs (nested too deeply to classify)"


# Secret material guardrail 1 forbids reading into context. The deny list in
# `.claude/settings.json` covers the `Read` tool; Bash is the other way to put a
# file in front of the model, and with prompts bypassed nothing else stopped
# `cat .env`. Matched on a token's basename, so `cat app/.env` and `cp .env
# /tmp/x` are caught along with the bare name. Adopting projects extend this
# the way they extend SAFE_BASH; `test_gnhf_guard.py` asserts it stays a
# superset of the shipped `Read(...)` deny rules, so the two cannot diverge.
SECRET_BASENAMES = (
    ".env", ".env.*", "*.pem", "*serviceaccount*.json", "*.key",
    # SSH private keys, by their real names rather than an `id_*` glob
    # that would also swallow `id_mapping.json`.
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "id_ed25519_sk",
    "id_ecdsa_sk",
)
# The non-secret neighbours. `.env.*` is the right pattern for the deny list and
# the wrong one for a committed example file, and a guard that refuses
# `cat .env.example` is a guard somebody switches off.
SECRET_BASENAME_EXCEPTIONS = (
    ".env.example", ".env.sample", ".env.template",
    "*.pub",  # the public half of a key pair is not secret material
)

# A redirect target the guard cannot resolve to a path: `~` is expanded by the
# shell to a home directory outside the repo, and a `$` is a variable whose
# value the guard never sees. Fail closed, the same as an unresolvable command
# word.
_UNRESOLVABLE_TARGET = re.compile(r"^~|\$")
# `2>&1` and `3>&-` redirect to a descriptor, not to a file.
_FD_TARGET = re.compile(r"^&\d*-?$|^\d+$")


def _redirect_targets(tokens: list) -> list:
    """Every operand a redirection operator points at.

    `_segments` drops these so they never become a command word, which is also
    why nothing used to look at them. A process substitution (`<(`, `>(`) opens
    a subshell, so what follows is a command and not a target."""
    out = []
    for index, token in enumerate(tokens[:-1]):
        if not _PUNCTUATION.match(token) or not ("<" in token or ">" in token):
            continue
        if "(" in token:
            continue
        target = tokens[index + 1]
        if not _PUNCTUATION.match(target):
            out.append(target)
    return out


def _writes_outside(tokens: list, repo_root, cwd):
    """The first redirection target that lands outside the repository, or None.

    The Edit/Write/NotebookEdit branch of `classify` has always confined the
    edit tools. A shell redirection is the other way to create a file, so
    `echo pwned > /tmp/outside.txt` was an unconfined write the enforcement map
    already claimed was impossible."""
    root = Path(repo_root).resolve()
    for target in _redirect_targets(tokens):
        if target.startswith("/dev/"):
            continue  # /dev/null and /dev/stderr; /dev/tcp is _network_redirect's
        if _FD_TARGET.match(target):
            continue
        if _UNRESOLVABLE_TARGET.search(target):
            return target
        path = Path(target)
        resolved = (path if path.is_absolute() else Path(cwd) / path).resolve()
        if not resolved.is_relative_to(root):
            return target
    return None


def _reads_secret(tokens: list):
    """The first token naming secret material, or None."""
    for token in tokens:
        if _PUNCTUATION.match(token):
            continue
        name = Path(token).name
        if not name:
            continue
        if any(fnmatch.fnmatchcase(name, p) for p in SECRET_BASENAME_EXCEPTIONS):
            continue
        if any(fnmatch.fnmatchcase(name, p) for p in SECRET_BASENAMES):
            return token
    return None


def _tokenize(command: str) -> list:
    """Shell-aware tokens for one line. Backticks become `$ ;` so their
    contents are classified as their own command, and so a substitution in
    command-word position (`` `echo curl` https://x ``) leaves behind a `$`
    the command-word rule refuses - the same shape `$(echo curl) https://x`
    already had.

    `commenters` is cleared because bash starts a comment only at the start of
    a word: `shlex`'s default would drop `; git push` from `echo done#; git
    push`, which bash runs. A `ValueError` propagates - a line the guard
    cannot tokenise is one it cannot judge, so the caller blocks it."""
    lexer = shlex.shlex(command.replace("`", " $ ; "), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def _segments(tokens: list) -> list:
    """Split a token list at shell operators; each part is its own command.

    Separators (`;`, `|`, `||`, `&`, `&&`, `(`, `)`) start a new command.
    Redirections (`>`, `>>`, `<`, `<<`, `<<<`, `>&`, `&>`, `>|`, and the `2` of
    `2>`) do not: bash accepts them before, between and after a command's
    arguments without moving the command word, so the operator and its target
    are dropped and the segment continues. Promoting a redirect target used to
    make `>/dev/null git push` read as a command named `/dev/null`.

    A process substitution (`<(`, `>(`) is a separator *and* a redirection,
    and what follows it is a command, not a target. Dropping it deleted the
    command word - `diff <(curl a) <(curl b)` read as `diff a b` - and fired
    on routine `diff <(sort a) <(sort b)` too, so the rule was mis-specified
    rather than incomplete. A target is therefore dropped only after an
    operator that opens no subshell, and only when it is a word: the `<(` in
    `cat < <(curl x)` is an operator, not the `<`'s target."""
    out, current = [], []
    drop_next = False
    for token in tokens:
        punctuation = bool(_PUNCTUATION.match(token))
        if drop_next:
            drop_next = False
            if not punctuation:
                continue  # the redirect target, not a command word
        if not punctuation:
            current.append(token)
            continue
        redirection = "<" in token or ">" in token
        separator = (
            bool(set(token) & {";", "(", ")"})
            or "&&" in token
            or "||" in token
            or (not redirection and bool(set(token) & {"|", "&"}))
        )
        if redirection and current and current[-1].isdigit():
            current.pop()  # the file descriptor of `2>file`
        if separator:
            out.append(current)
            current = []
        drop_next = redirection and "(" not in token
    out.append(current)
    return [segment for segment in out if segment]


def _operands(args: list) -> list:
    """Non-flag arguments."""
    return [arg for arg in args if not arg.startswith("-")]


def _pm_subcommand(args: list):
    """Return ("blocked", None), ("exec", rest) or (None, None).

    The first operand is the subcommand, and only PM_LOCAL_SUBCOMMANDS is
    allowed through: an unrecognised one is treated as network-capable. That
    is what covers npm's alias thicket (`in`, `isntall`, `clean-install`,
    `install-ci-test`) and the operations nobody enumerated (`adduser`,
    `unpublish`, `dist-tag`, `pnpm fetch`) without a list to keep current. A
    bare `yarn` installs, so no subcommand at all is blocked too, unless the
    invocation only asks for a version or help.

    Flags that swallow their value are skipped, so `pnpm --dir apps install`
    and `npm --registry https://evil.tld install` still land on the
    subcommand - except when the value *is* a local subcommand, because
    pnpm's `-w` is a boolean and `pnpm -w run lint` must keep working."""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.startswith("-"):
            if arg in PM_VALUE_FLAGS and index + 1 < len(args):
                value = args[index + 1]
                # No workspace or registry is named `install`; if one is, the
                # flag is being used to hide the subcommand.
                if value in PM_NETWORK_SUBCOMMANDS:
                    return "blocked", None
                if value not in PM_LOCAL_SUBCOMMANDS:
                    index += 2
                    continue
            index += 1
            continue
        if arg == "exec":
            rest = args[index + 1 :]
            return "exec", rest[1:] if rest[:1] == ["--"] else rest
        if arg in PM_LOCAL_SUBCOMMANDS:
            return None, None
        return "blocked", None
    if set(args) & PM_INFO_FLAGS:
        return None, None
    return "blocked", None


def _git_config_names_a_program(args: list) -> bool:
    """A `git -c KEY=VALUE` assignment git might execute. The value is a
    program the guard cannot see, so the assignment is allowed only for
    settings that name no program."""
    for index, arg in enumerate(args):
        if arg != "-c" or index + 1 >= len(args):
            continue
        key = args[index + 1].split("=", 1)[0].lower()
        if key not in GIT_SETTINGS_THAT_NAME_NO_PROGRAM:
            return True
    return False


def _network_redirect(tokens: list) -> bool:
    """A redirection whose target is /dev/tcp or /dev/udp, which bash turns
    into a socket. The target is dropped by `_segments`, so it is checked
    here, before the segment it belongs to loses it."""
    for index, token in enumerate(tokens[:-1]):
        if not _PUNCTUATION.match(token) or not ("<" in token or ">" in token):
            continue
        if _NETWORK_DEVICE.match(tokens[index + 1]):
            return True
    return False


def _git_subcommand(args: list):
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.startswith("-"):
            if arg in GIT_VALUE_FLAGS:
                index += 2
                continue
            index += 1
            continue
        return arg, args[index + 1 :]
    return None, []


def _node_source(args: list) -> str:
    """What node will run: "code" (`-e`, `-p`, `-r`), "script" (a file
    operand), "info" (a flag that prints and exits) or "stdin".

    The old rule keyed the stdin case on an empty argument list, so any flag
    that was not an eval flag reopened it: `node -` and
    `node --experimental-vm-modules` both run what the pipe hands them. An
    interpreter reads stdin unless an explicit script operand is present."""
    for arg in args:
        if arg == "-":
            return "stdin"
        if not arg.startswith("-"):
            return "script"  # the script path; the rest are its arguments
        if arg in NODE_INFO_FLAGS:
            return "info"
        if arg in NODE_EVAL_FLAGS or arg.split("=", 1)[0] in NODE_EVAL_FLAGS:
            return "code"
        if _SHORT_FLAG_CLUSTER.match(arg) and set(arg[1:]) & NODE_EVAL_SHORT:
            return "code"
    return "stdin"


def _reads_stdin(args: list, info_flags: set) -> bool:
    """The same rule for an interpreter whose flag grammar is not worth
    modelling: no script operand means it runs what the pipe hands it."""
    for arg in args:
        if arg == "-":
            return True
        if not arg.startswith("-"):
            return False  # the script path
        if arg in info_flags:
            return False
    return True


def _inline_eval_flag(name: str, args: list) -> bool:
    """`perl -we` is `perl -e` with `-w` glued on, the same shape `node -pe`
    already handled. Exact flag matching missed every cluster."""
    letters = INLINE_EVAL_LETTERS[name]
    return any(
        _SHORT_FLAG_CLUSTER.match(arg) and set(arg[1:]) & letters for arg in args
    )


def _python_source(args: list) -> tuple:
    """What the interpreter will run: ("code", None) for `-c`, ("module",
    name) for `-m`, ("script", path) for a file operand, ("info", None) for a
    flag that prints and exits, or ("stdin", None).

    Python parses a short-flag cluster left to right and lets `-c` and `-m`
    swallow whatever follows, in the same token or the next one: `-c`, `-Ic`,
    `-cimport os`, `-m pip`, `-mpip` and `-Im pip` are all the same
    invocation, and exact flag matching saw only two of them. `-W` and `-X`
    take a value, so their value is stepped over rather than mistaken for the
    script path, which is what let `python3 -X dev -c ...` through.

    Anything with no script operand left is stdin. Keying that on an empty
    argument list let one harmless flag reopen it: `python3 -u` and
    `python3 -i` both run what the pipe hands them."""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "-":
            return "stdin", None
        if not arg.startswith("-"):
            return "script", arg  # the rest are the script's arguments
        if arg in PYTHON_INFO_FLAGS:
            return "info", None
        if arg.startswith("--"):
            # No long option runs code; only one takes a value.
            index += 2 if arg in PYTHON_VALUE_LONG_FLAGS else 1
            continue
        step = 1
        cluster = arg[1:]
        for position, letter in enumerate(cluster):
            tail = cluster[position + 1 :]
            if letter == "c":
                return "code", None
            if letter == "m":
                return "module", tail or (
                    args[index + 1] if index + 1 < len(args) else ""
                )
            if letter in PYTHON_VALUE_LETTERS:
                step = 1 if tail else 2  # `-Xdev` carries its value, `-X dev` does not
                break
        index += step
    return "stdin", None


def _module_blocked(module: str, args: list) -> bool:
    """A blocked `-m` module, unless the invocation only asks it to explain
    itself: `python3 -m venv --help` installs nothing, and informational flags
    on blocked modules are the shape that trains people to switch a guard
    off."""
    if set(args) & INFO_FLAGS:
        return False
    return (
        module in PYTHON_MODULE_BLOCKED
        or module.split(".")[0] in PYTHON_MODULE_BLOCKED
    )


def _takes_separate_value(flag: str) -> bool:
    """Whether a flag might swallow the token after it. A bare short cluster
    (`-I`, `-n`) or a bare long option (`--jobs`) can; one that already carries
    its value (`-I{}`, `-n1`, `--output=x`) cannot, and reading `echo` as the
    value of `-I{}` lost the command word of `xargs -I{} echo {}`."""
    if _SHORT_FLAG_CLUSTER.match(flag):
        return True
    return flag.startswith("--") and "=" not in flag


def _wrapper_target(args: list, skip: int = 0) -> list:
    """The command a wrapper (`sudo`, `timeout`, ...) runs, past its own flags,
    their values, and the operands the wrapper takes for itself.

    An operand counts as the wrapper's own only when it is not a command the
    guard knows, so `timeout 30 curl x` steps over the duration while
    `flock lockfile git push` still finds the push and `timeout 30 grep curl f`
    still finds the grep rather than the word `curl` inside it."""
    for index, arg in enumerate(args):
        if arg.startswith("-"):
            continue
        known = Path(arg).name.lower() in KNOWN_COMMANDS
        if index and _takes_separate_value(args[index - 1]) and not known:
            continue  # the flag's value
        if skip and not known:
            skip -= 1  # the wrapper's own operand: a duration, a lock file
            continue
        return args[index:]
    return []


def _classify_wrapper(args: list, target: list, depth: int, confine=None) -> tuple:
    """A wrapper given arguments whose target the guard cannot find is a
    command it cannot judge, not an empty one."""
    if args and not target:
        if set(args) & INFO_FLAGS:
            return True, ""  # `timeout --help` wraps nothing
        return (
            False,
            "blocked in unattended runs (a wrapped command the guard cannot resolve)",
        )
    return _classify_segment(target, depth + 1, confine)


def _shell_c_argument(args: list):
    """The script `sh -c` / `bash -lc` is about to run, if there is one.

    `None` for a trailing `-c` as well as for no `-c` at all: returning `""`
    there was falsy but not `None`, which made a bare `sh -c` the one place in
    the file where cannot-resolve stopped meaning deny."""
    for index, arg in enumerate(args):
        if arg == "-c" or (_SHORT_FLAG_CLUSTER.match(arg) and "c" in arg[1:]):
            return args[index + 1] if index + 1 < len(args) else None
    return None


def _classify_segment(tokens: list, depth: int = 0, confine=None) -> tuple:
    if depth > _MAX_DEPTH:
        return False, _NESTED_TOO_DEEP
    while tokens:
        if tokens[0] in SHELL_DEFINITION_KEYWORDS:
            tokens = tokens[1:]
            if len(tokens) > 1 and tokens[1] == "{":
                tokens = tokens[1:]  # the construct's name, not a command word
            continue
        if tokens[0] in SHELL_KEYWORDS or _ENV_ASSIGNMENT.match(tokens[0]):
            tokens = tokens[1:]
            continue
        break
    if not tokens:
        return True, ""

    if not _RESOLVED_COMMAND_WORD.match(tokens[0]):
        return False, "blocked in unattended runs (unresolvable command word)"

    # macOS filesystems are case-insensitive, so `cUrL` runs curl. `Path` has
    # no name for `.`, so the token itself stands in.
    name = Path(tokens[0]).name.lower() or tokens[0].lower()
    args = tokens[1:]

    if name in SCRIPT_SOURCERS:
        return False, "blocked in unattended runs (a shell script the guard cannot read)"

    if name in ARG_WRAPPERS:
        return _classify_wrapper(
            args, _wrapper_target(args, ARG_WRAPPERS[name]), depth, confine)
    if args and (name, args[0]) in CONTAINER_ALIASES:
        args = args[1:]  # `docker container run` is `docker run`
    if args and (name, args[0]) in EXEC_WRAPPERS:
        skip = EXEC_WRAPPERS[(name, args[0])]
        return _classify_wrapper(args[1:], _wrapper_target(args[1:], skip), depth, confine)
    if args and (name, args[0]) in ALIAS_WRAPPERS:
        alias = [ALIAS_WRAPPERS[(name, args[0])]] + args[1:]
        return _classify_segment(alias, depth + 1, confine)
    if name in SHELL_RUNNERS:
        script = _shell_c_argument(args)
        if script is None:
            if set(args) & INFO_FLAGS:
                return True, ""  # `bash --version` prints and exits
            # A shell with no `-c` reads its script from stdin, a here-document
            # or a file, none of which the guard can see: `echo 'curl x' | sh`.
            return False, "blocked in unattended runs (a shell script the guard cannot read)"
        return _classify_command(script, depth + 1, confine)
    if name == "eval":
        return _classify_command(" ".join(args), depth + 1, confine)

    if name in SAFE_BASH:
        operands = _operands(args)
        if operands and operands[0] in SAFE_BASH[name]:
            return True, ""

    if name == "git":
        if _git_config_names_a_program(args):
            return False, "blocked in unattended runs (git configuration that names a program)"
        subcommand, rest = _git_subcommand(args)
        if subcommand in GIT_BLOCKED_SUBCOMMANDS:
            return False, "blocked in unattended runs (remote git actions)"
        if subcommand == "remote" and _operands(rest):
            return False, "blocked in unattended runs (remote git actions)"
        if subcommand == "archive" and any(a.startswith("--remote") for a in rest):
            return False, "blocked in unattended runs (remote git actions)"
        if subcommand == "config" and ("--global" in rest or "--system" in rest):
            return False, "blocked in unattended runs (machine-wide git configuration)"
        return True, ""

    if name in PACKAGE_MANAGERS:
        verdict, rest = _pm_subcommand(args)
        if verdict == "blocked":
            return False, "blocked in unattended runs (package manager network operations)"
        if verdict == "exec" and rest:
            # depth + 1, not 0: `npm exec -- npm exec -- ...` is nesting too.
            # The recursion was always bounded - each `npm exec --` eats two
            # tokens - and a reset counter never allowed an evil tail either.
            # It is fail-closed hygiene: past the cap the guard stops
            # resolving, so it has to stop allowing however the nesting is
            # spelled.
            return _classify_segment(rest, depth + 1, confine)

    if name in ("node", "nodejs"):
        source = _node_source(args)
        if source == "code":
            return False, "blocked in unattended runs (inline code execution)"
        if source == "stdin":
            return False, "blocked in unattended runs (a script the guard cannot read)"

    if _PYTHON_COMMAND.match(name):
        source, value = _python_source(args)
        if source == "code":
            return False, "blocked in unattended runs (inline code execution)"
        if source == "module" and _module_blocked(value, args):
            return False, "blocked in unattended runs (a module that reaches the network)"
        if source == "stdin":
            return False, "blocked in unattended runs (a script the guard cannot read)"

    if name in INLINE_EVAL_LETTERS and _inline_eval_flag(name, args):
        return False, "blocked in unattended runs (inline code execution)"

    if name in STDIN_INTERPRETERS and _reads_stdin(args, STDIN_INTERPRETERS[name]):
        return False, "blocked in unattended runs (a script the guard cannot read)"

    if name in BLOCKED_SUBCOMMANDS:
        blocked, label = BLOCKED_SUBCOMMANDS[name]
        if set(_operands(args)) & blocked:
            return False, f"blocked in unattended runs ({label})"

    if name in BLOCKED_COMMANDS:
        return False, f"blocked in unattended runs ({BLOCKED_COMMANDS[name]})"

    return True, ""


def _classify_command(command: str, depth: int = 0, confine=None) -> tuple:
    """Lines first: a newline is a command separator in bash but plain
    whitespace to `shlex`, so tokenising the whole string judged a multi-line
    command on its first command word only.

    Length first of all: `shlex` costs about n^1.8, so a megabyte of padding
    ahead of `; curl https://evil` outran the hook timeout, and a hook that
    times out does not block."""
    if depth > _MAX_DEPTH:
        return False, _NESTED_TOO_DEEP
    if len(command) > _MAX_COMMAND_LENGTH:
        return False, "blocked in unattended runs (command too long to parse safely)"
    for line in command.splitlines():
        try:
            tokens = _tokenize(line)
        except ValueError:
            return False, "blocked in unattended runs (the guard cannot parse this command)"
        if _network_redirect(tokens):
            return False, "blocked in unattended runs (network commands)"
        secret = _reads_secret(tokens)
        if secret is not None:
            return False, (
                f"blocked in unattended runs (reads secret material: {secret})")
        if confine is not None:
            outside = _writes_outside(tokens, *confine)
            if outside is not None:
                return False, (
                    f"blocked in unattended runs (writes outside the repository:"
                    f" {outside})")
        for segment in _segments(tokens):
            allowed, reason = _classify_segment(segment, depth, confine)
            if not allowed:
                return allowed, reason
    return True, ""


def classify(tool_name: str, tool_input: dict, repo_root, cwd) -> tuple[bool, str]:
    """Return (allowed, reason). Reason is set only when blocked."""
    if tool_name in NETWORK_TOOLS:
        return False, f"{tool_name} is blocked: no external connections in unattended runs"

    if tool_name in EDIT_TOOLS:
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        path = Path(raw)
        resolved = (path if path.is_absolute() else Path(cwd) / path).resolve()
        if not resolved.is_relative_to(Path(repo_root).resolve()):
            return False, f"edit outside the repository is blocked: {resolved}"

    if tool_name == "Bash":
        return _classify_command(
            tool_input.get("command", ""), confine=(repo_root, cwd))

    return True, ""


def main() -> int:
    """Exit 2 is the only code a PreToolUse hook treats as blocking; every
    other non-zero exit is a non-blocking hook error and the tool runs. So
    anything unexpected here - malformed JSON, an event shape we did not
    anticipate, a bug - has to end at 2 as well."""
    try:
        event = json.load(sys.stdin)
        repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        allowed, reason = classify(
            event.get("tool_name", ""),
            event.get("tool_input") or {},
            repo_root=repo_root,
            cwd=event.get("cwd") or os.getcwd(),
        )
    except Exception as error:  # noqa: BLE001 - fail closed on anything
        print(f"gnhf guard: blocked (the guard could not judge this call: {error})",
              file=sys.stderr)
        return 2
    if allowed:
        return 0
    print(f"gnhf guard: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
