# one-molecule documentation

These pages document a proposed layout for Molecule. One `molecule.yml` at the project root
declares the scenarios as a tree, and shared playbooks live once under `playbooks/molecule/`
and are referenced by name. This is proposed design, not current Molecule behavior. Existing
directory layouts keep running unchanged.

## The layout on one page

[The pattern](the-pattern.md) is the short statement of the layout: what the root file holds,
where the shared playbooks live, and why the config sits at the project root.

## The pages

The rest of the set follows the Diataxis structure, one page per kind of reading.

| Page | Kind | Read it to |
|---|---|---|
| [Getting started](getting-started.md) | Tutorial | Build a scenario tree from nothing, one stage at a time |
| [Migrating](migrating.md) | How-to | Convert an existing per-scenario layout, one recipe per task |
| [Reference](reference.md) | Reference | Look up what a key is and what the run does with it |
| [Explanation](explanation.md) | Explanation | Understand why one layout is less work for the test author |

## The worked examples

The repository carries real projects under `examples/`. Each keeps its original layout in
`before/` and the converted root file in `after/molecule.yml`. The [migrating](migrating.md)
recipes point to the matching example where one exists.
