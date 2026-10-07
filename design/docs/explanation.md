# Why one molecule.yml is easier for the person writing the tests

This page is about the author writing Molecule tests, and why declaring every scenario in one
root `molecule.yml` is less work than a directory per scenario. For the authoring surface see
[the pattern](the-pattern.md), for every key see the [reference](reference.md), to build the
file from nothing see [getting started](getting-started.md), and to convert an existing project
see [migrating](migrating.md).

## The problem: shared setup has nowhere to live

Molecule's only scope larger than a single scenario is the whole run. A scenario is one
environment, one converge, one verify, one state. Above that there is nothing until you reach
the entire invocation. So the moment two scenarios need to share something, whether that is a
converge playbook, a driver block, a platform, or an environment they both test against,
there is no place in Molecule's model to put it.

The author still has to put it somewhere, so a project's test config spreads across many
files:

- one `molecule.yml` in each scenario directory, most of it repeated from the next,
- a base `config.yml` for the settings every scenario shares,
- `shared_state: true` and a scenario that must be named `default`, when several scenarios
  test against one environment,
- playbooks copied into each scenario directory, symlinked between them, or pulled in through
  a small shim.

Each of those answers the same missing scope. To see how one scenario is configured, the
author reads its own file, then the base config, then works out whether `shared_state` applies.

## The idea: every scenario in one file

The author declares every scenario as a named entry in a single `molecule.yml` at the project
root. The file holds:

- the scenarios, each a named entry under `scenarios:` rather than a directory,
- the config they share, once, in a top-level `defaults:` block,
- each platform, once, in a top-level `platforms:` catalog,
- which scenarios test against another's environment, by nesting them under its `children:`.

The file carries config, never content. Playbooks stay playbooks, and the file references them
by path through `playbooks:`, a shorthand for the `provisioner.playbooks` mapping Molecule
already has. Several scenarios can name the same file, so a shared playbook is written once and
read by many.

## Nothing you write today is lost

Every part of today's layout has a place in the single file.

| Today | In the single file |
|---|---|
| A scenario directory's `molecule.yml` | An entry under `scenarios:`, with the same keys |
| A base `config.yml` | The top-level `defaults:` block |
| An inline platform list | The same list, or names from the catalog |
| A stage playbook in the scenario directory | Left unset, and Molecule's default discovery finds it |
| `shared_state: true` with a `default` scenario | A `default` root with the other scenarios as its children |

The keys on an entry are Molecule's own keys, validated by Molecule's own schema for each one.
Nothing about what a scenario does changes. Only where it is declared changes.

The direction that matters is from today's layout to the single file. Anything a project does
today can be written in the single file, and the [converter](converter/) writes the single file
back out as the per-scenario files Molecule reads, so the result runs on Molecule as it is. A
project that keeps its scenario directories runs unchanged, `shared_state` included.

The single file can say a few things today's layout cannot, such as a platform defined once
and selected by name. Those are additions on top, and the converter turns them into ordinary
scenario config.

## Why one file is easier for the author

Shared config is written once. A key under `defaults:` applies to every scenario that does not
set it, and mappings merge, so a scenario that sets only its own `verify` still receives the
shared `create`, `converge` and `destroy`. There is nothing to keep in sync across directories.

A platform is written once. A root scenario with no `platforms:` selects the whole catalog,
and each selection gets its own instance, named for the scenario.

The whole test structure is visible in one file. The scenarios, what they share, and which ones
depend on another are declared together rather than spread across directories whose
relationships you reconstruct by reading each one.

## When you need a parent, and when you only need shared config

A parent is for a dependency, not for shared configuration, and the two are easy to tell
apart with one question. If the shared thing were absent, would the scenario be unable to run,
or merely unconfigured?

Unable to run is a dependency, and it wants a parent. A host the scenario tests against, or a
directory tree it writes into: without those there is no run, so the scenario that builds them
is the parent.

Merely unconfigured is not a dependency. Independent scenarios that happen to share playbook
paths, a driver block, or a test sequence are not depending on each other, they are repeating
configuration. That is what `defaults:` is for. Molecule already merges each scenario over a
base config, and `defaults:` is that base config written in the same file. Parenting
independent scenarios to a shared node to save that repetition invents a dependency that is
not real, and makes scenarios that could stand up their own instances share one.

Use a parent for what one scenario genuinely needs another to build. Use `defaults:` for
settings that several scenarios merely repeat.

## What happens to `shared_state`

`shared_state` is the one setting Molecule has today for a set of related scenarios. It makes
a scenario named `default` build an environment that every other scenario reuses. The
environment's owner has to be called `default`, and nothing in the files says which scenarios
depend on it.

In the single file the same relationship is written directly. `default` is a root, and the
scenarios that test against it are nested under its `children:`. A child selects no platforms
of its own and shares its parent's instances. `shared_state` is not a key in the single file,
because the nesting says what it said.

A project that stays in its scenario directories keeps `shared_state` with Molecule's own
meaning, with no deprecation and no alias.

## What it looks like on a project

The `collection-shared-state` example under `examples/` is a collection with two roles that
both write into one application tree on one host. Today that needs `shared_state: true` in a
shared `extensions/molecule/config.yml`, a `default` scenario that builds the host and the
tree, and a scenario directory for each role.

In the single file `default` is a root and the two role scenarios are its children. The
driver, the shared `create`, `converge` and `destroy` playbooks and the connection settings sit
once in `defaults:`, and the platform sits once in the catalog. Each scenario names only what
is its own, its `verify` playbook, and `default` adds its own `create` and its test sequence.

The converter writes that file back as `config.yml` with `shared_state: true` and one
`molecule.yml` per scenario, each child carrying the parent's platform entry, with no notice.

## Where to go next

For how the root `molecule.yml` is structured and why it sits at the project root, read
[the pattern](the-pattern.md). For every key, read the [reference](reference.md). To build the
file step by step, read [getting started](getting-started.md).
