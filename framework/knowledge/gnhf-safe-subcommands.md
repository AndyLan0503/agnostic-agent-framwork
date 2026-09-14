---
type: mechanism
title: The gnhf guard allows local-only subcommands of blocked tools
description: The unattended-run guard whitelists specific safe subcommands of otherwise-blocked tool families.
tags: [gnhf, containment, agents, security]
timestamp: 2026-09-14
id: gnhf-safe-subcommands
related: [handoffs-are-files]
confidence: high
sources: ["framework/scripts/gnhf_guard.py", "framework/scripts/test_gnhf_guard.py"]
---

## Fact

The unattended-run guard blocks tool
families (`terraform`, `helm`, remote git, ...) but whitelists specific
subcommands in `SAFE_BASH` (framework/scripts/gnhf_guard.py). Criterion for
adding one - all four must hold:

1. No network connection under any usage.
2. No remote mutation.
3. No secret reads.
4. No flag can introduce a remote source (`helm template --repo`,
   `terraform plan`'s backend access - excluded for exactly this).

Chaining cannot ride through, but not for the reason this card used to give.
The guard no longer matches a safe pattern against the whole command string:
it splits the command on newlines, tokenises with `shlex`, splits at shell
operators, and classifies each segment on its own command word. `terraform fmt
&& curl ...` is blocked at the `curl` segment, and `cd apps && pnpm install`
at the `pnpm` one. Add new entries with a test in `test_gnhf_guard.py` first.

The guard is defense, not proof, and it carries known residual holes - listed
in its own docstring and repeated here, because AGENTS.md's enforcement map
names this card as where they live. Every entry below was re-probed against
the current `framework/scripts/gnhf_guard.py` and is open:

- **enumeration residue** - several tables are enumerations, and an
  enumeration is always one name behind the world: a shell missing from
  `SHELL_RUNNERS` (`ion -c`, `murex -c`, `ksh88 -c`), a wrapper missing from
  `ARG_WRAPPERS` (`valgrind`, `mpirun`, `srun`, `qemu-x86_64`), a package
  manager missing from `BLOCKED_SUBCOMMANDS` (`conan`, `composer`, `cpanm`,
  `apt-get`, `apk`, `nix-shell -p`, `stack`, `mix`).
- **write-then-execute** - `node ./payload.js`, `python3 scripts/payload.py`,
  `make test` through an edited Makefile, `make -f evil.mk`. Anything the run
  can write and then execute through an allowed invocation is outside what
  command-line pattern matching can reach.
- **argument-borne code** - interpreters that take code in an argument the
  guard does not model: `awk 'BEGIN{system(...)}'`, `find . -exec curl {} \;`,
  `vim -c '!curl ...'`, `sed -e '1e curl ...'`.
- **remote-resolving builds** - `cargo`, `go`, `mvn`, `dotnet` fetch
  dependencies with no distinguishing subcommand to block.
- **container runtimes past `docker run`** - `docker run`, `docker exec` and
  `docker create` (and their `podman` and `docker container ...` spellings)
  now resolve past the wrapper's own operand to the real command word, the way
  `timeout` resolves past its duration, and an image-only `docker run` is
  blocked because the image's `ENTRYPOINT`/`CMD` is a command word the guard
  cannot read. `docker compose` is not covered: `docker compose run svc curl
  ...` and a compose file the run wrote itself both execute through it,
  `docker start` replays a container created before the rule existed, and the
  standalone `docker-compose` binary is not modelled at all.
- **wrapper-target heuristic** - finding a wrapper's target is a guess, not a
  parse. An operand after a flag counts as the command only when the guard
  already knows the name, so a wrapper flag that takes a separate value can
  still shadow a command the guard does not know.
- **command-borne writes** - the guard confines shell *redirections* to the
  repository, so `echo x > /tmp/out` is blocked, but a write carried in a
  command's own arguments is not modelled: `cp secret /tmp/x`, `tee /tmp/x`,
  `dd of=/tmp/x`, `rsync`-shaped copies, an editor invoked on an outside path.
  Confining those means modelling every command's argument grammar, which is
  the enumeration problem again.
- **the secret list is an enumeration** - `SECRET_BASENAMES` blocks Bash from
  reading `.env`, `*.pem`, `*.key`, service-account JSON and SSH private keys,
  and `test_gnhf_guard.py` holds it to a superset of the `Read(...)` deny rules
  in `.claude/settings.json`. A credential under a name nobody listed
  (`config/prod.yaml`, `tokens.txt`) is read like any other file, and a path
  the shell expands (`cat $SECRETS`) is not resolved.

None of these close with another rule. They close with network isolation: an
unattended run that must stay local runs inside a network-isolated container.
The guard raises the cost of an accident and blocks the obvious paths - it
does not make the run local, and nothing in this file should be read as a
claim that it does.
