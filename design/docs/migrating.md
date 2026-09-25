# Migrating an existing layout to one root molecule.yml

Task recipes for converting a project from the per-scenario directory layout to the
single top-level `molecule.yml` proposed in `the-pattern.md`. Each recipe is a short
procedure. For the authoring surface these recipes target, read `the-pattern.md`. For
why the tree is less work than the directory layout, read `explanation.md`.

This is a proposed design, not shipped molecule behavior. Every recipe describes how a
migration would work under the proposal. Steps that rely on a part still marked Proposed
(the single-file discovery mode, the `runtime:` envelope, playbook references by collection
FQCN) say so where they occur, so nothing here reads as available in molecule today.

Each of the nine projects under `examples/` carries its converted root file at
`after/molecule.yml`, beside the original layout in `before/`. The recipes below use
`arista.avd` (`examples/arista-avd/`) and the upstream
[`ansible.platform`](https://github.com/ansible/ansible.platform) collection as the concrete
cases, and point to the matching example where one exists. `ansible.platform` has no
converted example under `examples/`, so recipe 1 describes what its conversion would do.

## Before you start

Two questions decide the shape of every migration.

1. Does one scenario build something the others cannot run without? That is a
   dependency, and it becomes a parent and its children. An image, a template, a server
   stood up once and tested against many times is a dependency.
2. Or do the scenarios merely repeat the same config while each stands up its own
   environment? That is not a dependency. It becomes shared `defaults:`, and the
   scenarios stay independent roots.

The test is one question, from `explanation.md`: if the shared thing were absent, would
the scenario be unable to run, or merely unconfigured. Unable to run is a parent.
Unconfigured is `defaults:`. Reaching for a parent where `defaults:` is what you need
invents a dependency, orders scenarios that could run alone, and skips all of them when
the shared node fails.

## Recipe 1: Convert a shared_state project to a tree

For a project where one scenario stands up an environment with `create`/`destroy` and
every other scenario tests against it under `shared_state: true`. Worked case:
`ansible.platform`, 23 scenario directories under `extensions/molecule/`: a shared base
config, a `default` scenario that stands up a mock server, and 22 mock scenarios that test
against it.

1. Find the setup scenario. It is the one whose `test_sequence` runs `create` and
   `destroy` and whose playbooks stand the shared environment up. In `ansible.platform`
   it is `default`, which starts a mock server and tears it down.
2. Make that scenario the root of the tree and make every other scenario its child.
   Under the proposed single root file, the root is one entry in `scenarios:` and the
   rest nest under its `children:`. The nesting is the parent edge.
3. Let ownership follow the playbook references. The root references its own
   `create`/`destroy`, so it owns the environment. The children reference neither, so
   they own nothing and start from a snapshot of the root. There is no ownership flag to
   set. Ownership is read off the create reference.
4. Move the settings every child repeated into one top-level `defaults:` block: the
   driver, the platforms, the verifier, the environment, the provisioner config options.
   A child keeps only what makes it different.
5. Move the shared playbooks into `playbooks/molecule/` and reference each by name.
   A playbook set the children share can ride on the root's own `defaults:` block, which
   applies to the root and everything below it. Written once, read by many. See recipe 6
   for folding near-identical playbooks together.
6. Drop the per-scenario inventory copies. The root owns the inventory and the tree
   snapshots it down to the children, so a child sees the root's hosts without declaring
   anything.
7. Drop `shared_state: true`. It is not a key in the root file, and the nesting now
   declares the relationship it stood in for. A project left in its scenario directories
   keeps `shared_state` with Molecule's own meaning, unchanged.

For `ansible.platform` the config collapse would replace the shared base config and the 23
per-scenario `molecule.yml` files with one root `molecule.yml`. Folding the mock scenarios'
near-identical playbooks onto one shared set is a further step, the content refactor in
recipe 6, not something the conversion does on its own.

## Recipe 2: Convert a per-role roles/*/molecule/ layout to one root config

For a collection that carries a separate `molecule/` directory inside each role, plus a
helper role that every scenario pulls in for shared setup. This is the
`prometheus-community` shape from the repository README, where a `_common` role stands in
for the missing shared home. The converted root file is
`examples/prometheus-community/after/molecule.yml`.

1. Choose the root file location. It is the collection root, the one place that exists
   for a collection, a role, and a playbook project alike (`the-pattern.md`).
2. Declare each role's scenario as an entry in the root `scenarios:` list. A scenario
   becomes a named entry, not a directory under a role.
3. Decide whether the roles share a real dependency or only config. Per-role test
   scenarios that each build their own environment are independent, so they stay roots in
   the list and share through `defaults:`. Use a parent only where one role genuinely
   builds what another needs.
4. Replace the helper role used for shared setup with shared playbooks under
   `playbooks/molecule/`. The setup that lived in the helper role becomes a converge or
   prepare playbook referenced by the scenarios that need it. The helper role existed
   because shared content had nowhere else to live.
5. Move each role's converge and verify playbooks into `playbooks/molecule/` and
   reference them by name.

## Recipe 3: Convert a delegated-driver, many-scenario collection

For a collection with many scenarios that each connect to hosts under a delegated or
ansible-native driver and share a large amount of config. Worked case: `arista.avd`, 30
scenarios under `extensions/molecule/`, collapsed to one root `molecule.yml` in
`examples/arista-avd/after/`.

1. Read the scenarios as independent first. In `arista.avd` each scenario stands up and
   tears down its own instances and shares only configuration, so none of them is a
   parent of another. They become a flat list of roots under `scenarios:`, not a tree.
2. Lift the shared config into one top-level `defaults:` block: the executor backend and
   its inventory argument, the shared play environment (`ansible.env`), the ansible
   config, the default sequences, the dependency and verifier settings. In the worked file
   this is a single `defaults:` block above the list.
3. Give each scenario only its own difference. Most `arista.avd` scenarios reduce to a
   name, a converge playbook reference, and a per-scenario sequence where it diverges
   from the default. A scenario that needs an extra environment variable or a different
   inventory carries just that key bare on the node.
4. Reference the playbooks. In the worked file they are named by collection FQCN, for
   example `arista.avd.molecule_ansible_only_converge`. That form is Proposed and assumes
   molecule's FQCN stage-reference fix (molecule issue 4244). Until that fix lands, the
   same playbooks are referenced by relative path into `playbooks/molecule/`. The layout
   is identical either way, only the reference form changes.
5. Keep the python and ansible-core grid with the outer caller. That toolchain matrix
   belongs to whatever calls molecule, such as tox or CI, running the molecule CLI as a
   plain caller. The root file does not carry it. In the root file the `runtime:` envelope
   selects the execution method and, under the `ee` method, one run cell per execution
   environment. The `runtime:` envelope is Proposed.

## Recipe 4: Move a project-local ../shared/ directory into playbooks/molecule/

For a project with a top-level `molecule/` directory and a project-local `../shared/`
folder that the scenarios reach into for common playbooks. This is the
`dev-sec/ansible-collection-hardening` shape from the repository README. The converted
root file is `examples/dev-sec-hardening/after/molecule.yml`.

1. Move the contents of `../shared/` into `playbooks/molecule/`. Under the collection's
   own `playbooks/` tree these are ordinary playbooks, addressable by name and lintable
   like any other content, rather than files reached through a relative path out of a
   scenario directory.
2. Reference each shared playbook from the scenarios that use it, by name. The
   `../shared/` folder existed because molecule had no shared home above a scenario. It
   has nothing left to do once the playbooks live under `playbooks/molecule/`.
3. Fix any path that counted `../` to climb out of the scenario directory. A path written
   once in a shared location must mean the same file from every scenario, so it must not
   depend on how deep the referring scenario sits (`explanation.md`, and the anchors work
   behind it).
4. Declare the scenarios in the root `scenarios:` list, sharing their common config
   through `defaults:`.

## Recipe 5: Add a child scenario to an existing tree

For a tree that already has a root and you want a new scenario that depends on the root's
environment.

1. Add the new scenario as an entry nested under its parent's `children:` in the root
   file. The nesting is the parent edge, so there is no parent name to type and no second
   file to edit.
2. Give the child only its own keys: its `name`, the converge and verify playbooks it
   runs, and any config that differs from what the tree already hands down.
3. Reference the child's playbooks from `playbooks/molecule/`. It starts from the
   parent's snapshot for the environment, so it does not restate the driver, the
   platforms, or the inventory.
4. Leave `create`/`destroy` off the child unless it stands up its own instances. Without
   a `create` the child is not a creator, owns nothing, and tests against the parent's
   environment. If it does need its own instances, give it its own `create`/`destroy`
   references and it owns what its `create` produces while still starting from the
   parent's snapshot (`reference.md`).

## Recipe 6: Share one converge or verify playbook across scenarios

For scenarios that run near-identical converge or verify steps.

1. Put one copy of the playbook under `playbooks/molecule/`.
2. Reference it from every scenario that runs it. Referencing the same file from several
   scenarios is how the shared content is written once and read by many.
3. Pass each scenario's difference as variables on the node rather than as a separate
   playbook.

Folding many near-identical playbooks onto one parameterized trio is an author-side
content refactor, not something the conversion does for you. Molecule gives the shared
content a home under `playbooks/molecule/`. Reducing several playbooks to one is your
edit. In `ansible.platform` many of the 22 mock scenarios run the same converge,
verify, and cleanup skeleton and differ mainly in the module they call and a few
variables. Those could fold onto one shared playbook set driven by a per-child vars block,
while any scenario that genuinely diverges keeps its own playbooks. One task limit sets
the boundary: a task's module name cannot be Jinja-templated in Ansible, so a shared
converge that dispatches different modules needs a small dispatch shim rather than a bare
templated module key. Fold together only the playbooks that really are the same shape.

## Recipe 7: Test one node without its siblings

For running one scenario in a tree and getting only what it depends on.

1. Select the node by name, the same `-s` selection molecule uses today.
2. Expect its ancestors to come along. A request for a node is a request for the node and
   its full ancestor chain, because a child cannot run without the parent that builds its
   environment. Selection narrows what is tested, never what is depended on.
3. Expect nothing sideways or below. Ancestor closure is upward only. A targeted run
   pulls in the target and its ancestors and never its siblings, its cousins, or its
   descendants.
4. Expect a standing ancestor to be left alone. An ancestor whose environment is already
   up and converged is trusted, not rebuilt. An ancestor that is not standing runs its own
   full sequence, minus `destroy`, including its verify, before the target starts.

If the target turns out to need a scenario that is not on its ancestor chain, the repair
is to declare that dependency. An opt-in selector to also run the scenarios that share the
target's parent covers the case where you cannot declare it yet (`reference.md`). It is
opt-in because a targeted run must not fan out sideways on its own.

## Recipe 8: Run a tree in parallel with --workers

For running independent nodes concurrently. `--workers` exists in molecule today as an
experimental flag, in collection mode, and the proposal reshapes what it schedules.

1. Run with `--workers <n>`. It is a single global cap on how many scenarios are in flight
   at once, oriented to machine capacity.
2. Expect the gate to order the tree for you. A root runs first. Its children become
   runnable only after it succeeds and are skipped if it fails. Siblings in the same wave
   run concurrently.
3. Keep siblings independent. Siblings in one wave run at the same time and take no
   snapshot from each other, so two siblings must not name the same host or step on each
   other's state. Ancestor-to-descendant handoff is ordered by the gate and stays safe.
4. Where two siblings must run one after the other without depending on each other, put
   them in different waves with `wave:`. Nodes that share a parent run in ascending wave
   order, and a wave starts once every node in a lower wave has completed its whole
   subtree. Where one needs the other's result, nest it under that sibling instead.
5. Expect the root phase to idle slots. A single-tree project leaves the other workers
   idle while the root runs alone, because the root has to finish before any child is
   runnable. The idle slots fill once there is more than one tree.

If you would rather not reason about sibling concurrency at all, run with `--workers 1`,
which serializes the run while still following the tree.

## Recipe 9: Refuse implicit provisioning for a costly layer

For a layer that should never be stood up implicitly, such as a driver that costs real
money, a shared lab owned by someone else, or a CI job whose whole point is to assert the
layer was already there.

1. Set `missing_parent: fail` on the scenario whose ancestor must already be standing. The
   default is `create`, which builds a missing ancestor the way any dependency system
   satisfies a dependency. `fail` refuses instead.
2. Expect a loud refusal, not a silent skip. When the ancestor is not standing, the run
   stops and names the ancestor and the command that would build it.
3. Override per invocation with `--missing-parent` where one run needs the other policy.

`missing_parent` is a per-scenario behavior key, so it is committed with the project and
does not have to be remembered on the command line.

## Where to go next

For the structure of the root file, how playbooks are referenced, and why the config
lives at the project root, read `the-pattern.md`. For the full key and behavior spec, read
`reference.md`. For the reasoning behind declaring scenarios as a tree, read
`explanation.md`.
