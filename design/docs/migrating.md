# Migrating an existing layout to one root molecule.yml

Task recipes for moving a project from per-scenario directories to the single top-level
`molecule.yml`. Each recipe is a short procedure. For the authoring surface these recipes
target, read [the pattern](the-pattern.md). For every key, read the [reference](reference.md).
For why one file is less work, read the [explanation](explanation.md).

Every part of today's layout has a place in the single file. The [converter](converter/) turns
the single file back into the per-scenario files today's Molecule reads, so you can run the
result with Molecule as it is and compare it with what you had.

The recipes point at the four synthetic examples under `examples/`. Each is a project in the
single-file form, with its root file at `examples/<name>/molecule.yml`.

| Example | Shape |
|---|---|
| `playbooks` | A playbook project with two independent scenarios |
| `roles` | Three standalone roles, one scenario each |
| `collection` | A collection with two roles, one scenario each |
| `collection-shared-state` | A collection whose scenarios test against one shared environment |

## Before you start

One question decides the shape of every migration. If the shared thing were absent, would a
scenario be unable to run, or merely unconfigured?

1. Unable to run is a dependency. The scenario that builds the shared environment becomes a
   parent, and the scenarios that need it become its children. Today that is
   `shared_state: true` with a `default` scenario.
2. Merely unconfigured is shared config. It goes in the top-level `defaults:` block, and the
   scenarios stay independent roots.

Reaching for a parent where `defaults:` is what you need invents a dependency. See
[the explanation](explanation.md#when-you-need-a-parent-and-when-you-only-need-shared-config).

## Recipe 1: Convert a project of independent scenarios

For a project whose scenarios each stand up their own instances and share only config. Worked
cases: `examples/collection/`, `examples/roles/` and `examples/playbooks/`.

1. Create `molecule.yml` at the project root, the folder that holds `galaxy.yml` in a
   collection, or the top of the repository for roles and playbooks.
2. Add one entry under `scenarios:` for each scenario directory. Its `name:` is the directory
   name.
3. Move the keys of the base `config.yml`, if the project has one, into the top-level
   `defaults:` block.
4. Move each scenario's `molecule.yml` keys onto its entry, as bare keys.
5. Move any key every scenario repeats into `defaults:`, and delete it from the entries. A
   mapping merges, so an entry that sets one key inside `playbooks:` still receives the rest
   from `defaults:`.
6. Leave a stage playbook that lives in a scenario directory unset, and Molecule's default
   discovery still finds it there. Reference a shared playbook by a path relative to the
   project root, such as `playbooks/molecule/create.yml`.
7. Convert the file with the scenarios directory the project uses, `extensions/molecule` for a
   collection or `molecule` for a role or playbook project, and compare the output with the
   files you started from (see [Recipe 7](#recipe-7-check-the-conversion)).

A project that keeps one `molecule/` directory inside each role, `roles/<role>/molecule/`,
converts the same way. The converter writes it back as a top-level `molecule/` directory with
one scenario per role, which is how `examples/roles/` runs.

## Recipe 2: Convert a shared_state project to a tree

For a project where a scenario named `default` stands up an environment and every other
scenario tests against it under `shared_state: true`. Worked case:
`examples/collection-shared-state/`.

1. Make `default` the one entry under `scenarios:`.
2. Nest every other scenario under `default`'s `children:`. The nesting declares what
   `shared_state` declared.
3. Move the base config's other keys into the top-level `defaults:` block, and drop
   `shared_state: true`. It is not a key in the single file.
4. Keep the platforms on `default`, inline or as catalog names. A root with no `platforms:`
   selects the whole catalog.
5. Remove `platforms:` from every child. A child selects none and shares its parent's
   instances.
6. Remove any `create` or `destroy` playbook a child sets for itself. A child may still inherit
   them from `defaults:`, because under `shared_state` Molecule runs those two stages only for
   `default`.
7. If `default` sets `scenario.test_sequence`, keep both `create` and `destroy` in it.
8. Convert the file. The converter writes the base config with `shared_state: true` and gives
   each child `default`'s platform entries. An empty notice list means the tree matched
   `shared_state` exactly.

The converter writes a tree as `shared_state` only in this shape: one root named `default`,
every other scenario a direct child of it. Any other shape gets a `lost` notice that names the
condition that failed. See
[the tree today's Molecule runs](reference.md#the-tree-todays-molecule-runs).

## Recipe 3: Define a repeated platform once

For scenarios that each write the same inline platform entry.

1. Add the entry once to the top-level `platforms:` catalog, with a `name:` and Molecule's own
   platform keys.
2. Remove the inline entry from each root scenario that used it. A root with no `platforms:`
   selects the whole catalog. To select only some entries, list their catalog names.
3. Update anything that names the old instance. A catalog selection's instance is named
   `<scenario name>-<catalog name>`, so a root `motd` selecting `instance` gets
   `motd-instance`.
4. Move per-instance inventory variables into the entry's `host_vars:`. Each selecting
   scenario receives them under its own instance name. A scenario's own
   `provisioner.inventory.host_vars` for that instance still wins where both set a variable.

An inline platform object stays valid, and keeps its `name` exactly as written. A catalog name
and an inline name that match in one run is an error.

## Recipe 4: Share one converge or verify playbook

For scenarios that run the same converge or verify steps. Worked case: `examples/roles/`.

1. Put one copy of the playbook in a shared folder under the project root, such as
   `playbooks/molecule/`.
2. Reference it once from the `playbooks:` key in `defaults:`.
3. Pass each scenario's difference in rather than writing a separate playbook. In
   `examples/roles/` the one `converge.yml` includes the role named by `MOLECULE_SCENARIO_NAME`,
   and each scenario is named for the role it tests.
4. Set the stage bare on the scenarios that genuinely differ. A bare key overrides `defaults:`
   for that scenario only.

## Recipe 5: Add a child to a shared_state tree

For a tree with a `default` root, where a new scenario tests against `default`'s environment.

1. Nest the new scenario under `default`'s `children:`.
2. Give it its `name:` and the playbooks it runs itself, such as its own `verify`.
3. Leave `platforms:`, `create` and `destroy` off it. It shares `default`'s instances.

## Recipe 6: Run scenarios in parallel

For running independent scenarios at the same time. This needs a collection, a project with a
`galaxy.yml`.

1. Set the `workers` key at the top of the file to an integer, `cpus` or `cpus-1`. The default
   is 1, one scenario at a time.
2. Pass the same value as `--workers` when you run the converted files. Today's Molecule takes
   the cap only from the flag, so the converter reports the key as `lost` and names the flag.
3. Do not combine a value above 1 with `--destroy=never`. Molecule rejects it.
4. Check the children of a `default` root. They run against the same host, so a child that
   changes state another one reads makes their order matter, and nothing guards against that.

## Recipe 7: Check the conversion

For confirming that the single file says what the old layout said.

1. Paste the file into the [converter](converter/), or run it from a clone of this repository.

   ```
   python3 tools/converter/cli.py molecule.yml --scenarios-dir molecule --out <dir>
   ```

2. Read the notices.

   | Notice | Means |
   |---|---|
   | `error` | The file breaks the spec, such as a key the spec does not declare |
   | `unresolved` | The design does not decide the case, so the converter picks no answer |
   | `lost` | The single file carries it and today's Molecule cannot, such as a `wave` |
   | `unsupported` | Today's Molecule rejects the combination at run time |

3. Compare the written scenario files with the ones you started from. Playbook paths differ in
   form only, because a relative path is written as `${MOLECULE_PROJECT_DIRECTORY}/<path>`.
4. Run the written files with `molecule test --all` from the project root.

## Where to go next

For every key and how a value resolves, read the [reference](reference.md). For the structure
of the root file, read [the pattern](the-pattern.md). For the reasoning, read the
[explanation](explanation.md). To learn the file from nothing, read
[getting started](getting-started.md).
