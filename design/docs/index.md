# one-molecule documentation

These pages document the single-file `molecule.yml`, spec version 0.3.0. One `molecule.yml` at
the project root declares every scenario, the config they share, and the scenarios that test
against another's environment. Everything a project writes in per-scenario files today has a
place in it, and the [converter](converter/) writes it back out as the per-scenario files
today's Molecule reads. A project that keeps its scenario directories runs unchanged.

## The layout on one page

[The pattern](the-pattern.md) is the short statement of the layout: what the root file holds,
where the shared playbooks live, and why the config sits at the project root.

## The pages

The rest of the set follows the Diataxis structure, one page per kind of reading.

| Page | Kind | Read it to |
|---|---|---|
| [Getting started](getting-started.md) | Tutorial | Build a root `molecule.yml` from nothing, one stage at a time |
| [Migrating](migrating.md) | How-to | Convert an existing per-scenario layout, one recipe per task |
| [Reference](reference.md) | Reference | Look up what a key is and how a value resolves |
| [Explanation](explanation.md) | Explanation | Understand why one file is less work for the test author |

## The worked examples

The repository carries examples under `examples/`. Four are synthetic, written for this
repository, and each is a project in the single-file form with its root file at
`examples/<name>/molecule.yml`: `playbooks`, `roles`, `collection` and
`collection-shared-state`. Each is a preset on the converter page. The others are upstream
projects, each with its original layout in `before/` and the converted root file in `after/`.
The [migrating](migrating.md) recipes point to the synthetic examples.
