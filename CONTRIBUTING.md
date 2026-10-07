# Contributing

This repository is a proof of concept for a single top-level `molecule.yml`. This page is the
mechanics: how to set up, what to edit, and how to prove a change is good before you push. Three
other files own the rules, and this one does not repeat them.

| Read | Owns |
|---|---|
| `README.md` | What the project is and what the examples measure |
| `design/README.md` | The map of the design corpus |
| `design/AUTHORING.md` | The law for authoring a design source |
| `AGENTS.md` | The ground rules for AI coding tools and the human driving one |

## Setup

You need Python 3 and git. The exact Python version CI uses is pinned in
`.github/workflows/design-spec.yml`.

```console
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install pre-commit pyyaml check-jsonschema yamllint
pre-commit install
./tools/install-hooks.sh
```

`pre-commit` installs the hook tool versions pinned in `.pre-commit-config.yaml` into its own
environments on first run, so the direct installs above are only for running the same checks by hand.
`pyyaml` is the one real runtime dependency, because `tools/build.py` imports it.

The gitleaks hook is the one exception to that list. It is a Go program, so the first run builds it
and needs network. You do not need Go installed, because `pre-commit` fetches a toolchain when it
finds none.

| Setup step | What it protects against |
|---|---|
| `pre-commit install` | A commit that violates a schema, the house style, the clean room, leaves the generated schema stale, or carries a secret |
| `./tools/install-hooks.sh` | A push that publishes a path meant to stay local. Run once per clone, because git hooks are not cloned |

## Editor setup

Every `design/data/<doc>.yml` starts with a modeline naming its validator:

```yaml
# yaml-language-server: $schema=../structure/<doc>.schema.yml
```

Any editor running a YAML language server that honors that modeline will complete keys and underline
a violation as you type, so you find a schema error while writing rather than at commit time. The
capability is what matters, not the brand: the same modeline works in any editor with a YAML language
server client. Point your editor at the repo-root `.yamllint` as well, so its YAML findings are the
ones the gates use.

## Making a change

| To change | Edit | Then |
|---|---|---|
| The design itself | `design/data/<doc>.yml` | Validate it against `design/structure/<doc>.schema.yml` |
| The shape a design source must take | `design/structure/<doc>.schema.yml` | Re-validate every source it covers |
| The config surface the work delivers | `spec/molecule-config.schema.yml` | Bump `x-spec.version`, `$id` and the description, then run `python3 tools/build.py` to regenerate |
| Documentation | `design/docs/` | Follow the process that page's set describes |
| A worked example | `examples/<project>/after/` and its `README.md` | Keep `before/` exactly as it came from upstream |

Two folders are never hand-edited. `generated/` is build output, and a hand edit is overwritten by
the next build and fails CI. `vendor/` is upstream material, which is re-vendored rather than patched.

## Running the gates

Everything CI runs, runs locally:

```console
pre-commit run --all-files
python3 tools/build.py --check
yamllint --strict -c .yamllint .
./tools/check-private-paths.sh
```

`pre-commit run --all-files` covers the first three. Run them singly when you want the failure on its
own.

The gitleaks hook scans what you staged, which is all a pre-commit gate can see. The `secrets` CI job
scans the whole history instead, so a credential that was committed and later deleted still fails the
build. To run that scan yourself, with gitleaks on your path:

```console
gitleaks git --redact --verbose --config .gitleaks.toml .
```

| Failure | Means |
|---|---|
| `<doc>.yml against its validator` fails | The source no longer matches its shape. Fix the source, or widen the validator on purpose |
| `example configs against the generated config schema` fails | An `after/molecule.yml` uses a key or value the config schema does not admit |
| `STALE: generated/...` | `spec/molecule-config.schema.yml` changed without a regenerate. Run `python3 tools/build.py` |
| `PROSE: ...` | A semicolon, em dash, or en dash reached published prose. Split the clause or reword |
| `CLEAN ROOM: ...` | Published text carries private working context, such as a home path or a link into a folder a public reader cannot open. Move the content rather than rewording to dodge the pattern |
| `SELFTEST: ...` | A linter's own fixtures stopped firing, so the gate is no longer proving anything. Fix the pattern, not the fixture |
| `yamllint` findings | Every yamllint rule here is an error, never a warning. There is nothing to defer |
| `BLOCKED: git is tracking paths ...` | Something listed in `tools/private-paths.txt` got staged. Untrack it and keep the working copy |
| `Detect hardcoded secrets` fails | gitleaks matched a credential. Rotate it first, before anything else, because it is burned the moment it lands in a file. Then remove it from the content. Amending the commit does not undo a push, and the old commit stays fetchable, so rotation is the fix and deletion is only cleanup. A genuinely throwaway test value, such as a disposable VM's admin password, keeps its value and gets an inline `# notsecret` comment on the same line, which leaktk/patterns' shipped global allowlist honours. Never add an allowlist, a stopword, a `.gitleaksignore` entry or a `gitleaks:allow` comment. `.gitleaks.toml` is generated, and the only allowlists in it are the ones shipped upstream with the gitleaks default ruleset and leaktk/patterns |

`./tools/check-private-paths.sh --selftest` proves the push guard still fires in both directions,
against a throwaway repo. Run it if you change the path list.

## Conventions that will trip you up

- **No semicolons, no em dashes, no en dashes** in prose, in markdown and in YAML string values alike.
  Code blocks and inline code spans are exempt, because punctuation there is syntax. `tools/build.py`
  enforces this and CI backstops it.
- **A key whose name starts with `_` is source-only.** It is stripped at any depth when
  `spec/molecule-config.schema.yml` is emitted, so notes and provenance belong there or in a YAML
  comment. Neither reaches the artifact.
- **Everything tracked is publishable.** Anything that is not goes under `internal/`, which is
  gitignored. Never force-add it, never cite it from a published file.
- **Stage explicit paths.** Never `git add -A` and never `git commit -a`. A blanket add is how local
  material becomes a public commit.
- **Every new gate needs a fixture that proves it fires.** A check that silently stops matching passes
  everything. The linters in `tools/build.py` and the push guard each carry must-catch and must-allow
  fixtures, and a new one carries its own.
- **`yamllint .` walks the whole tree.** The repo `.yamllint` ignores the tool environments, so build
  your virtualenv at `.venv` and not under some other name, or the lint scope picks up third-party
  YAML that is none of your business.
