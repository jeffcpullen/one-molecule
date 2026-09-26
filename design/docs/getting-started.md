# Getting started: build a scenario tree

This is a start-to-finish walk-through. You begin with a single scenario and grow it, one step
at a time, into a scenario tree, ending with a mental model of how it runs. It builds up in four
stages: a single scenario, two independent scenarios, a dependency between two scenarios, and a
multi-level tree that both branches and deepens.

This walk-through describes a proposed layout. Molecule discovers scenarios as directories
today and has no scope larger than a single scenario, so the single root `molecule.yml`, the
tree edges, and the gating behavior shown here are not how Molecule runs at the moment. Read
this as how the proposed layout would be authored and run. Where a command or a behavior
depends on something proposed, the text says so.

For the authoring surface, see [the pattern](the-pattern.md), and for every option, see the
[reference](reference.md). For why one layout is easier than a directory per scenario, see the
[explanation](explanation.md). This page is the guided path through them.

## Stage 1: a single scenario

Start with the smallest thing that runs: one scenario, no tree at all. A scenario is one
environment, one converge, one verify. This one stands up an instance, configures it, and
checks the result.

### The root file

Put one `molecule.yml` at the project root, and put the playbooks it references under
`playbooks/molecule/`. Nothing else is required.

```yaml
# molecule.yml  (project root)
---
scenarios:
  - name: base
    platforms:
      - name: base-instance
        image: registry.fedoraproject.org/fedora:41
    playbooks:
      create: playbooks/molecule/create.yml
      destroy: playbooks/molecule/destroy.yml
      converge: playbooks/molecule/base.yml
      verify: playbooks/molecule/verify.yml
```

`scenarios` is a list of root scenarios, and `base` is the only one here. Its keys sit bare on
the node, so they apply to `base` and nothing else, which is all there is at this stage. `base`
references its own `create` and `destroy`, so it owns the instances it stands up. Ownership is
read off that create reference, not off a separate key.

### Run it

```
molecule test
```

`base` runs its full sequence: `create` stands up the instance, `converge` runs `base.yml`,
`verify` runs `verify.yml`, and `destroy` tears the instance down at the end. This is one
scenario running on its own, the same shape Molecule runs today, with the config declared in a
root file rather than a scenario directory.

## Stage 2: two independent scenarios

Add a second scenario that has nothing to do with the first. Two scenarios are just two entries
in the `scenarios:` list, each a root, each owning its own instances. Neither depends on the
other.

The two share the same create and destroy playbooks, so declaring those on each node would
repeat them. Lift that shared config into a top-level `defaults:` block, which applies to every
node below it. Now it is written once, and each scenario declares only what is its own, its
platforms and its converge and verify.

```yaml
# molecule.yml  (project root)
---
defaults:
  playbooks:
    create: playbooks/molecule/create.yml
    destroy: playbooks/molecule/destroy.yml

scenarios:
  - name: web
    platforms:
      - name: web-instance
        image: registry.fedoraproject.org/fedora:41
    playbooks:
      converge: playbooks/molecule/web.yml
      verify: playbooks/molecule/verify-web.yml
  - name: db
    platforms:
      - name: db-instance
        image: registry.fedoraproject.org/fedora:41
    playbooks:
      converge: playbooks/molecule/db.yml
      verify: playbooks/molecule/verify-db.yml
```

`web` and `db` are both roots, and neither is a parent of the other. Both stand up their own
instances, so the `create` and `destroy` they share sit in `defaults:` and are inherited by
each. Ownership stays per node: each resolves a `create` reference, so each stands up and owns
its own instances. A bare key on a node, like each scenario's `platforms`, applies to that node
alone.

### Run them

```
molecule test
```

Both scenarios run. Because neither depends on the other, they have no ordering between them,
and they can run at the same time.

```
molecule test --workers 2
```

`--workers` runs independent roots concurrently. Selecting one scenario runs only that one,
since it depends on nothing else.

```
molecule test -s web
```

`--workers` exists in Molecule today for collection-mode scenarios. Running these root scenarios
from a single `molecule.yml`, and the scheduler that runs independent roots concurrently, are
part of the proposed behavior.

## Stage 3: one scenario depends on another

Independent scenarios are the common case. The tree is for the other case: one scenario needs an
environment that another scenario builds. That is a dependency, and you express it by nesting the
dependent scenario under the one it needs.

Here `app` needs the environment `base` stands up. Nest `app` under `base`'s `children:`, and
that nesting is the parent edge. `base` stays the root that owns the instances, and `app` runs
against them.

```yaml
# molecule.yml  (project root)
---
scenarios:
  - name: base
    platforms:
      - name: base-instance
        image: registry.fedoraproject.org/fedora:41
    playbooks:
      create: playbooks/molecule/create.yml
      destroy: playbooks/molecule/destroy.yml
      converge: playbooks/molecule/base.yml
      verify: playbooks/molecule/verify.yml
    children:
      - name: app
        playbooks:
          converge: playbooks/molecule/app.yml
          verify: playbooks/molecule/verify.yml
```

`app` is nested under `base`'s `children:`, so `app`'s parent is `base` with no other
declaration. `app` references its own converge playbook and the same
`playbooks/molecule/verify.yml` that `base` uses. That is one file referenced by two nodes,
written once, with no copy.

Here `create` and `destroy` sit on `base` itself, not in `defaults:`, so `app` does not inherit
them. `app` declares no `create` of its own either, so it stands up no instances. It runs
against the instances `base` created.

### Run it

```
molecule test
```

To see the structure the file declares, print the tree.

```
molecule matrix
```

Printing the declared tree from `molecule matrix`, and resolving a tree when you run it, are part
of the proposed behavior, not what these commands do today.

### What happened

Molecule reads the one root file and builds the tree. `base` is a root. `app` is `base`'s child.

`base` runs its full sequence: `create` stands up the instances, `converge` runs `base.yml`, and
`verify` runs `verify.yml`. `base`'s verify is the readiness gate. Its children do not start
until it passes.

Once `base` has verified, `app` starts. `app` begins from a snapshot of `base`, a copy of
`base`'s inventory taken once at `app`'s start. So the hosts `base` stood up are present for
`app` to test against, and `app` reads only its own copy after that. `app` runs `converge` with
`app.yml` and then `verify` with `verify.yml`.

Teardown runs deepest first. `app`'s cleanup runs, then `base`'s `destroy` tears down the
instances it owns. `app` owns no instances, so it destroys none.

The shape to hold onto: the parent builds and verifies an environment, its verify is the gate,
and the child starts from the parent's snapshot. That is the whole model. Stage 4 is more of it.

## Stage 4: a multi-level tree

A child can itself be a parent, and a parent can have more than one child. Combine the two and
you get a tree that branches where work is independent and deepens where one step needs the one
before it. This stage builds the satellite tree.

```
vm                          create/destroy, expensive, runs once
└── install-satellite       gate: satellite up and verified
    ├── org-and-auth        depends on the satellite
    └── repositories        depends on the satellite
        └── content-view    depends on repositories
```

`vm` stands up the machine and owns its instances. `install-satellite` depends on the vm, and
its verify gates everything below it. `org-and-auth` and `repositories` are siblings: both depend
on `install-satellite`, and neither depends on the other. `content-view` depends on
`repositories`, and nests under it.

### The satellite tree

`install-satellite` has two children, and one of them, `repositories`, has a child of its own.
The root owns create and destroy, exactly as `base` did in Stage 3. Each deeper node references
only its own converge and verify.

```yaml
# molecule.yml  (project root)
---
scenarios:
  - name: vm
    platforms:
      - name: vm-instance
        image: registry.fedoraproject.org/fedora:41
    playbooks:
      create: playbooks/molecule/create.yml
      destroy: playbooks/molecule/destroy.yml
      converge: playbooks/molecule/vm.yml
      verify: playbooks/molecule/verify-vm.yml
    children:
      - name: install-satellite
        playbooks:
          converge: playbooks/molecule/install-satellite.yml
          verify: playbooks/molecule/verify-satellite.yml
        children:
          - name: org-and-auth
            playbooks:
              converge: playbooks/molecule/org-and-auth.yml
              verify: playbooks/molecule/verify-org-and-auth.yml
          - name: repositories
            playbooks:
              converge: playbooks/molecule/repositories.yml
              verify: playbooks/molecule/verify-repositories.yml
            children:
              - name: content-view
                playbooks:
                  converge: playbooks/molecule/content-view.yml
                  verify: playbooks/molecule/verify-content-view.yml
```

`vm` is the root, so it carries the `create`, `destroy`, and `platforms` that stand the machine
up, the same way `base` did in Stage 3. Those are left off the deeper nodes here to keep the
tree readable. See Stage 3, or [derived ownership](reference.md#derived-ownership) in the
reference, for the root's create details.

### Branches run independently, depth runs in order

This tree has both shapes from the earlier stages. `org-and-auth` and `repositories` are
independent, the way the two roots in Stage 2 were, so once `install-satellite` verifies, both
can start, and they can run at the same time. `content-view` sits below `repositories`, the way
`app` sat below `base` in Stage 3, so it waits for `repositories` to verify first.

Each node's verify gates its children, the same rule at every depth. Depth is serial, because
each level waits on its parent's gate. Branches are not, because siblings do not depend on each
other.

### Selecting a node

Selecting a node runs that node and everything it depends on, which is its ancestors, and
nothing else.

```
molecule test -s content-view
```

Resolving the ancestor chain when you select a node is part of the proposed behavior.

`content-view` depends on `repositories`, which depends on `install-satellite`, which depends on
`vm`. Selecting `content-view` resolves that chain, root first: `vm`, then `install-satellite`,
then `repositories`, then `content-view`. For each ancestor, if it is already standing from an
earlier run it is left alone, and if it is missing it runs its own full sequence up to and
including its verify. Then `content-view` runs from its parent's snapshot.

`org-and-auth` does not run. It is a sibling of `repositories`, not an ancestor of
`content-view`, and selection covers the target and its ancestors only, never siblings.
Selection narrows what is tested, never what is depended on. An ancestor the run built to
satisfy the dependency is left standing at the end, so the next selection of a node in that
chain finds it already up.

## Where to go next

You now have the model: a single scenario, independent scenarios side by side, a dependency
expressed by nesting, and a tree that branches where work is independent and deepens where it is
not. Each node's verify gates its children, each child starts from its parent's snapshot, and
selecting a node pulls in its ancestor chain.

For the full key and behavior spec, the config scopes, and how a key resolves, read the
[reference](reference.md). For how the root file is laid out and why the config lives at the
project root, read [the pattern](the-pattern.md). For why the tree is less work than a
directory per scenario, read the [explanation](explanation.md). To convert an existing project,
read [migrating](migrating.md).
