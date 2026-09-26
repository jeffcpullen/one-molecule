# Reference: the single top-level molecule.yml

The lookup spec for the proposed single-config layout. It states what each key is and what the
run does with it. For the authoring surface, read [the pattern](the-pattern.md). For a guided
build of a tree, read [getting started](getting-started.md), and for converting an existing
project, read [migrating](migrating.md). For the reasoning behind the tree, read the
[explanation](explanation.md).

This describes a proposed design, not shipped Molecule behavior. The single-file surface as a
whole is proposed. Referencing playbooks by path through `provisioner.playbooks` is behavior
Molecule already has. Items that are proposed and not yet built are marked **Proposed** where
they appear.

## The root file

One `molecule.yml` at the project root holds the run configuration, the scenario declarations,
and the tree edges between scenarios. A scenario is a named entry in that file, not a
directory. The file carries config, never playbook content. Playbooks are referenced by path
and live once under `playbooks/molecule/` (see [the pattern](the-pattern.md)).

Root-file discovery is a second mode alongside directory globbing, not a replacement. Existing
directory layouts keep running unchanged. A tree is declared in the root file only.

Molecule runs one scenario, and the orchestrator runs everything above it: the tree, the
cascade, ordering, and every read across nodes. Each node reaches Molecule as one
single-scenario config in Molecule's own schema. No run-only, reserved structural, or
node-intrinsic key reaches Molecule.

## Top-level keys

The top level of the file is the run. It carries run-only keys bare and all cascading config
under a top-level `defaults:` block.

| Key | Class | What it is |
|---|---|---|
| `runtime` | run-only | The sealed execution the whole sequence runs inside. **Proposed** (see below) |
| `platforms` | run-only | The platform catalog. Each entry defines one platform once, selected by scenarios by name |
| `defaults` | reserved structural | The cascading config block for the run and everything below it |
| `scenarios` | reserved structural | The list of root nodes. Run level only |

`children:` is the third reserved structural key. It is a node key, not a run-level key, and
is covered under [Declaring the tree edge](#declaring-the-tree-edge).

There is no top-level `env:` key. Play environment is the config key `ansible.env`, which
cascades through `defaults:` (see [Environment](#environment)).

### runtime (Proposed)

`runtime:` is the run-only block that names the sealed execution the whole sequence runs
inside. It is declared once for the run and never sits on a node. `method:` is its
discriminator.

| Method | What it provides |
|---|---|
| `ee` | A container carries the controller toolchain. One run cell per execution environment |
| `host` | The ambient session, no isolation and no fan-out. This is today's behavior |
| `<custom>` | A registered runtime plugin that reads `additional_parameters` |

Two seams sit alongside the method:

- `executor:` selects how the control plane runs and defaults to `ansible-runner`. Molecule
  defines what to run and the executor decides how, whether local, remote podman, kubernetes,
  or AAP. ansible-runner is one implementation, never a binding.
- `build_method:` selects the ahead-of-time build plugin and defaults to `none`. Build is a
  separate phase and never part of the run. With `none` every referenced image must already
  exist. ansible-builder is one build plugin, never a binding. An EE is always built ahead of
  time, and at run time Molecule checks an EE is available and never builds it.

Under the `ee` method, `execution_environments:` is a list and each entry is one EE reference.
The runtime fans out one run cell per EE. python and ansible-core are provenance observed on a
`host` run, never a declared axis. The python and ansible-core grid is the outer caller's own
matrix, driven by a tool such as tox or CI that calls the Molecule CLI as a plain caller.
Molecule publishes no matrix config for an outside tool to read.

An EE reference takes one of two forms:

| Form | Shape | Cells |
|---|---|---|
| Compact | `repository/image:tag` or `repository/image@digest` | One cell |
| Discrete | `repository`, `image`, `name`, and `labels` written once, with `tags` and `digests` lists | One cell per tag and per digest |

The discrete form requires at least one of `tags` or `digests`, and both may coexist. A cell's
`name` is inferred as `{image}_{tag}` or `{image}_{last-6-of-digest}` when unset, and an
explicit `name` replaces the `{image}` prefix. Per EE, `pull_policy:` is one of `always`,
`missing` (the default), or `never`. Per EE, `build_opts` and `method_opts` are opaque bags for
the build plugin and the executor. Run-level `additional_parameters` carries a custom runtime's
config, opaque to Molecule.

`labels:` on an EE entry place it in the EE selection dimension, narrowed by `--label` and
`--skip-label` the same way as platforms and scenarios. A bare run executes every EE.

### platforms (the catalog)

The top-level `platforms:` is the catalog. Each entry defines one platform once by `name`,
with an opaque `vars` bag passed through to the create step and a `labels` list for
selection. A scenario's own `platforms:` is a selection of catalog names, or inline platform
objects for backward compatibility.

A root scenario with no `platforms:` selects the whole catalog. A child selects none of its
own and inherits the parent's shared inventory. Creation stays on the node, whose `create`
playbook stands up the selected platforms and consumes their `vars`. The catalog deduplicates
the definition, not the creation.

### Selection by label

`labels:` are selection membership. They sit on three dimensions: a catalog platform, a
scenario, and an execution environment. A label filters only the dimension it appears on.

| Flag | Effect |
|---|---|
| bare run | Executes every scenario, platform, and EE, because a label narrows only when named |
| `--label` | Narrows only the dimension its label appears on. Multiple labels union |
| `--skip-label` | Subtracts the items carrying that label from the run |

A label named for selection that matches nothing in the config is rejected, the way an unknown
field is.

### scenarios

`scenarios:` is a list of root nodes, run in wave order, and top to bottom in list order within
a wave. Each item is a node named by `name:`. A node nests its children under `children:`,
itself a list. Within a wave, list order is the order a serial run takes and the order the
`--workers` scheduler submits (see [Sibling waves](#sibling-waves)).

A node item mixes four kinds of key:

- a `defaults:` block: config for the node and its subtree,
- bare config keys: config for the node alone,
- the reserved structural key `children:`,
- the node's own intrinsic keys: `name:`, `shared:`, `missing_parent:`, `wave:`, and
  `labels:`.

### The node intrinsic keys

| Key | What it is |
|---|---|
| `name` | The node's identity in the list. How `-s` selects it. Unique across the run |
| `shared` | Default `true`. On a parent, `shared: false` stops that node sharing its inventory down to its children. It never gates creation |
| `missing_parent` | Per node, default `create`. What happens when a depended-on ancestor is not standing |
| `wave` | Integer, default `0`. The ordering tier among nodes that share a parent, roots included. Never cascades |
| `labels` | Selection labels for this scenario. Filter only the scenario dimension |
| `children` | The nesting bucket. A list of child nodes. Node only |

`playbooks:` is a top-level convenience alias for `provisioner.playbooks`, a config key
rather than an intrinsic one. It maps `create`, `destroy`, `converge`, `verify`, and the rest
by path, and is valid bare or inside a `defaults:` block.

`shared` sits on the parent as one subtree-wide boolean. There is no per-child form. The only
coherent reason a parent sets `shared: false` is that it is a prerequisite step whose instances
are not the runtime environment, such as an image builder or a registry setup: its children
depend on it completing and passing its gate, not on its hosts.

Sharing is within a tree only. There is no cross-tree share flag.

## Config scope and precedence

Config is placed in one of two spots on any node, and the spot is the scope.

| Placement | Where it sits | Applies to |
|---|---|---|
| `defaults:` | a `defaults:` block on the node | that node and everything below it. Overridable by a nearer `defaults:` or by a bare key on the target |
| Bare key | a config key directly on the node | that node only. It overrides the node's own `defaults:` for that node, and never cascades |

Two ideas repeat at every level: "here and below" is `defaults:`, and "for me specifically" is
a bare key. `defaults:` is the norm. A bare key is the exception, reached for only to override
a node's own default for the node alone.

A `defaults:` value covers the node that sets it as well as its subtree, so a node that wants
the same value for itself and its subtree writes it once. Config shared across a subtree lives
in the nearest common ancestor's `defaults:`. Config for a whole forest lives in the run's
`defaults:`.

The bare key exists for the dual-hat node. A root that creates instances declares the driver
and platform config it needs to create as bare keys, self only, never handed to children, and
declares what its descendants run under in `defaults:`. Same key name, two homes on one node,
two meanings.

### Resolution order

Resolving a config key path P for node N walks these layers, highest first:

> N's bare `P` then N's `defaults[P]` then the nearest ancestor's `defaults[P]` (walking up,
> parent first) then run `defaults[P]` then the built-in default.

P is a key path, not a top-level key. Mappings deep-merge across the layers, so a layer that
sets one key inside a mapping overrides only that key. A node that sets a bare
`playbooks.converge` still resolves `playbooks.create` from an ancestor's `defaults:`.

An empty value, null or the empty string, overrides every lower layer. A key whose resolved
value is empty is absent, so an empty value is how a node clears a key it would otherwise
receive.

A bare key never enters another node's resolution, because bare does not cascade. A key absent
everywhere takes Molecule's built-in default.

This is configuration inheritance: the deep merge Molecule already does between a base
`config.yml` and a scenario, now with the two-placement layering above. It is not the runtime
inventory snapshot, which is a separate channel covered under [State and the
snapshot](#state-and-the-snapshot).

### Which keys are config

A config key may sit bare or inside a `defaults:` block and resolves by the rule above. A
run-only key is a property of the invocation and does not cascade. A node-intrinsic key belongs
to exactly one node and is never inherited.

| Key | Class | Note |
|---|---|---|
| `driver` | config | Typically bare on a creating node, so it is not handed to children |
| `provisioner` | config | Bare or in `defaults:` |
| `verifier` | config | Bare or in `defaults:` |
| `dependency` | config | Bare or in `defaults:` |
| `ansible` | config | Bare or in `defaults:`. `ansible.env` is the play environment and cascades like any config key |
| connection settings | config | Bare or in `defaults:` |
| `platforms` (on a scenario) | config | A selection of catalog names, or inline platform objects. Consumed only by a node that creates its own instances |
| `playbooks` | config | Create and destroy are typically bare by convention, so a parent that creates does not hand creation to children |
| `shared` | node-intrinsic | Default on. On the parent, one subtree-wide boolean |
| `missing_parent` | node-intrinsic | Per node, default `create` |
| `wave` | node-intrinsic | Integer, default `0`. Ordering tier among nodes that share a parent |
| `labels` | node-intrinsic | Scenario selection labels. Filter only the scenario dimension |
| `runtime` | run-only | The sealed execution the sequence runs inside. Not per-node |
| `platforms` (top level) | run-only | The catalog. Each entry defines one platform once |
| `defaults` | reserved structural | The "this node and below" config block. Any node, and run level |
| `scenarios` | reserved structural | The tree bucket. Run level only |
| `children` | reserved structural | The nesting bucket. Node only |
| `name` | node-intrinsic | The node's identity |

The `defaults:` block accepts the full current Molecule scenario schema, `playbooks` included.
The keys that are not config are the ones this design adds: the reserved structural names and
the node-intrinsic keys. None collides with a Molecule config key at the same level.
Molecule's `shared_state` is not a key in the single file.

`platforms` on a non-creating node is permissive, with no diagnostic. An empty or absent
`platforms` is already a valid state in Molecule, and Molecule emits no warning for a
platforms-versus-driver mismatch. A node that creates nothing may carry a resolved `platforms`.
It is consumed only where the node creates and ignored otherwise.

## Declaring the tree edge

The edge is nesting the child under its parent's `children:` in the root file. The nesting is
the edge, and there is no `parent:` key.

One parent per child. A node with no parent is a root. More than one parent per child is not
supported. A conjunction is expressed by nesting one parent under the other. A cycle is an
error at tree build, naming the full cycle path.

Directory-path nesting, such as `appliance_vlans/merged`, is a naming convention only and never
infers an edge.

### What activates a tree

Nesting under `children:` is the only way to declare an edge, with no flag and no project
setting. Only the root file declares a tree.

A scenario in its own `<name>/molecule.yml` directory has no edge and runs as Molecule runs it
today. `shared_state` keeps Molecule's own meaning in a directory-mode project, with no
deprecation and no alias. It is not a key in the root file.

### missing_parent: build it, or refuse

`missing_parent: create | fail`, per scenario, default `create`. Overridden by
`--missing-parent`.

| Value | Effect when an ancestor is not standing |
|---|---|
| `create` (default) | Bring it up. A dependency system satisfies dependencies |
| `fail` | Refuse, naming the ancestor and the command that would build it |

`fail` is for the cases where implicit provisioning is the wrong answer rather than a
convenience: a driver that costs real money, a shared lab where the layer is somebody else's,
or a CI job whose whole point is to assert that the layer was already there.

### A partial run

Selection narrows what is tested, never what is depended on.

| Parent is | Effect |
|---|---|
| Not in this run's selection | Resolved anyway |

Selection covers the target and its ancestors, upward only. A targeted run never fans out
sideways or downward: no siblings, no cousins, no descendants.

Filling in an undeclared dependency, where a scenario turns out to need something that is not
on its chain, is a separate opt-in selector that also runs the scenarios sharing the target's
parent. It is a selector, so it stays on the command line, and it is opt-in. **Proposed**.

## Per-node lifecycle

Actions per node:

- `create` runs the node's `create` playbook and `destroy` runs its `destroy` playbook. On a
  node with no such playbook the action does nothing, though the default `test_sequence`
  lists it.
- `cleanup` undoes this node's own layer. Every node has it.
- Everything else (`dependency`, `syntax`, `prepare`, `converge`, `idempotence`, `side_effect`,
  `verify`) is per node as today.

A typical child sequence is `dependency, cleanup, syntax, prepare, converge, idempotence,
side_effect, verify, cleanup`. The leading cleanup clears that node's prior layer on a re-run,
and the trailing one undoes it at teardown. Both already exist in the default `test_sequence`.

### Traversal order

- Setup is pre-order. Root first, each node gated on its parent's verify.
- Teardown is post-order. Deepest first, up to the root. A child that owns instances has its
  `destroy` run here, before its ancestors'.

A node's trailing cleanup waits until its whole subtree completes, so a parent does not remove
the layer its children still depend on.

### The readiness gate

A parent's verify must pass before any child starts. That is the gate. A child begins from a
snapshot of its parent, so the environment the parent stood up is present for the child to test
against.

A parent is a dependency, so a run of any node resolves that node's full ancestor chain,
transitively, whether or not those ancestors were selected. Per ancestor, root first:

| Ancestor state | What runs |
|---|---|
| Standing | Nothing. It is already the layer the child needs |
| Not standing | Its own full sequence, minus `destroy`, including its `verify` |

Standing is read from the node's own state file, by the orchestrator: `converged`, plus
`created` when the node owns instances. A rebuilt ancestor runs its verify because the gate has
not yet passed for a layer this run just built. A standing ancestor is trusted rather than
re-verified.

An implicitly built ancestor is left standing when the run ends. The end-of-run report lists
it.

**Verify contract.** A node's `verify` must be side-effect free, repeatable, and must not
mutate the inventory, because the gate and the copy-at-start snapshot both depend on it.

### Retry

Retrying a node means: clean up its subtree post-order, then run the node's ordinary sequence,
whose leading `cleanup` clears its own prior layer. Nothing above it is touched, so the
expensive root survives. `molecule test -s <node>` is defined this way: clean up or destroy the
subtree below the node, run the node, and above it resolve the ancestor chain, leaving a
standing ancestor untouched and building one that is missing.

### Failure

| Event | Effect |
|---|---|
| A node fails any phase before its gate opens | Its descendants are skipped, with the phase named in the note |
| A sibling fails | That tree's not-yet-started siblings are skipped. Running ones finish |
| `--continue-on-failure` | Do not skip siblings either |
| Any failure | The run is red. `failed` outranks everything in the overall verdict |

Descendants are skipped, not failed, because nothing in them ran. The skip carries a reason.

### Teardown on failure

On failure, cleanups run post-order, always. `destroy` at each owning node is governed only by
the `--destroy` policy, with no failure-specific exception.

`--destroy` gains an `on-success` value, `always | on-success | never`, default `always`.
**Proposed**.

| Value | Meaning |
|---|---|
| `always` (default) | Destroy every owning node, pass or fail |
| `on-success` | Destroy only when the whole run is green. Keep everything when anything failed |
| `never` | Today's meaning, unchanged |

Anything left standing by `on-success` or `never` is listed at the end of the run, per node,
with the command to remove it. An implied teardown, such as retrying a parent tearing down its
subtree, is named before it runs on an interactive terminal, not only in the end-of-run
summary.

## Scheduling

`--workers` sets how many scenarios run at once. It is an experimental flag on `test`,
`destroy`, and `check` only, available in collection mode only, so a `galaxy.yml` is
required. It accepts an integer, `cpus`, or `cpus-1`, floored at 1. The unit of concurrency
is one whole scenario, with no concurrency inside a scenario, and it has no relation to
Ansible's `forks`.

### The scheduler

The scheduler submits what is ready and refills a freed slot with the next runnable unit. Every
node goes through the pool, roots included.

- A root in the lowest wave is runnable immediately, and its task runs its own sequence
  through `verify` inside the worker.
- On a node's success its children in the lowest wave become runnable and are submitted. On
  its failure its children are skipped and never submitted.
- A node's trailing `cleanup`, and its `destroy` where it owns instances, are each their own
  scheduled unit, runnable once the subtree has completed.

`--workers` is a single global cap on scenarios in flight. `--workers 1` is not a special
case, it runs through the one scheduler with the cap set to 1. A single-tree run with
`--workers 8` idles seven slots during the root phase, which is a cost of the gate
and disappears once a run has multiple trees.

### Ordering

Dependency is expressed by nesting, and order without dependency by `wave`.

| Need | How |
|---|---|
| A node needs another node's result | Nest it under that node |
| Nodes need order but no dependency | Declare it with `wave` |

Trees are independent by construction. If tree B needs tree A's result, they are not two trees
but one. Within a wave, submission order is list order and carries no meaning, and completion
order is arbitrary. Node names must not encode ordering.

### Sibling waves

`wave:` orders nodes that share a parent and do not depend on each other. Roots share the run,
the virtual root, as their parent, so `wave` orders roots too.

- `wave` is a node-intrinsic integer, default `0`, and never cascades.
- Wave numbers compare only between nodes that share a parent.
- Nodes that share a parent run in ascending wave order.
- Nodes in the same wave run concurrently, up to the `--workers` cap.
- A wave starts once every node in a lower wave has completed its whole subtree. A subtree is
  complete once its cleanup and destroy have run.
- A node never depends on a node in a lower wave. A failure skips nothing because of a wave
  boundary.

### Sibling independence

Siblings in one wave run concurrently, so they must be independent of each other.
Ancestor-to-descendant mutation is strictly ordered by the gate and is always safe, but
Molecule provides no guard rails for sibling independence, no name prefixes and no allocation.

| Need | Escape hatch |
|---|---|
| Safe together | Give them a shared parent |
| Needs another's result | Nest it under that sibling |
| Must run before or after, with no dependency | Put them in different waves |
| Do not want to reason about it | `--workers 1` |

A sibling collision surfaces as a nondeterministic, worker-count-dependent failure. Detecting
two concurrent siblings whose inventories name the same host and reporting the collision in
tree terms is **Proposed**.

### Fail-fast

Fail-fast is per tree. A failure in one tree does not stop other trees. Per-tree fail-fast
drops that tree's pending descendants from the runnable set and continues the loop. A
gate-based scheduler cancels nothing that has started, it stops submitting, so scenarios that
have not started are skipped and running ones finish. Teardown still runs for a failed tree.

## State and the snapshot

State is strictly per-node. Every node has one state file that it alone reads and writes. There
is no shared state file.

The snapshot flows one way, parent to child, never up and never sideways. Siblings take no
snapshot from each other. What flows down is the inventory, and only the inventory.

### The channel

The inventory directory is the channel, and the parent's snapshot is a named file inside it,
not the directory wholesale. Molecule regenerates `hosts`, `group_vars`, and `host_vars` before
every action, so the snapshot is written as a distinct file that the regeneration leaves alone
and Ansible merges natively as a second source in the same directory. Molecule keeps passing
exactly one `--inventory`, pointing at the node's own directory.

`instance_config.yml` does not flow down. It stays private to the node that created the
instances and is that node's ownership record. `ansible.cfg` is generated per node and is not
snapshotted.

### Copy at start

A child copies its parent's inventory into its own ephemeral directory once, at node start.
After the copy the child reads only its own files. The copy is of the parent only, not every
ancestor: the parent's own inventory is already parent-merged, so a deeply nested child never
needs to know its ancestors beyond its parent. A retry re-copies.

### Precedence

The merge is a deep merge with the child winning. Precedence is key-level, not whole-host: if
the parent has a host with `ansible_host` and `ansible_user` and the child sets `ansible_user`,
the child's value wins and `ansible_host` survives. Effective precedence runs root to leaf, so
a deeper node overrides a shallower one. Lists are replaced wholesale rather than concatenated.

### Group names and the per-node group

Because inventories merge, an ancestor and a descendant using the same group name land both
sets of hosts in one group. Snapshotted hosts appear in `all` and in whatever groups their
creator put them in. A node that wants to target only its own hosts should name its groups
distinctly, and its own `instance_config.yml` is the authoritative record of what it created.

Molecule additionally places each node's instances in one extra group named for the node, so
"the hosts I created" has a name the author can type. This is additive and renames nothing.

### Instance generation

Per-node state leaves one gap: a node's lifecycle flags are reset only by `destroy`, and a node
that owns no instances has no `destroy`, so a child's `prepared` would otherwise survive
forever. An owner stamps a new instance generation when its `create` succeeds, a node records
the generation its own flags were set against, and at node start a different generation
invalidates that node's `prepared` and `converged`. The orchestrator reads the owner's
generation, never the node, so no node opens another node's files. The owner is the nearest
ancestor that owns instances.

## Derived ownership

Ownership is the relationship between an object and the node whose `create` produced it. It
is derived from the `create` reference and never declared. There is no `owns_instances` key.

- A creator is a node with a defined `create`. A node that is not a creator owns nothing.
- A node's owned objects are recorded as the inventory and vars its `create` adds.
- An owned object need not be a machine.
- Ownership of an object never passes to another node.

Molecule ships no default `create` playbook, so a `create` is present only where the author put
one. `create` and `destroy` are typically bare by convention, so a parent that creates does not
hand creation to its children.

Any node, root or child, may be a creator. Sharing a parent's inventory down to a child and a
child creating its own objects are orthogonal: a child can start from the parent's snapshot
and still create its own.

### A node destroys only what it owns

- Molecule tears down an owned object only at its owner, and never runs an ancestor's
  `destroy` on behalf of a descendant.
- Post-order teardown runs a descendant's `destroy` before its ancestors'.
- Molecule ships no default `destroy` playbook, so a node with no `destroy` has nothing to run.
- `instance_config.yml` records the objects a node created, per node, and drives the common
  destroy playbook.

`create` and `destroy` are the author's own playbooks. `hosts: all` in a child's `destroy`
tears down snapshotted ancestor hosts, and that is the author's call. No inventory shaping
prevents it, because every instance is in `all` by construction.

## Provisioning

A `create` playbook often consumes an input that must exist before it runs, such as a
container image, a VM template, a base AMI, an OVA, a VPC, or an execution environment. The
tree fills that gap with an ordinary node. A node whose `create` builds the artifacts, whose
`verify` asserts they exist, whose `destroy` removes them, and whose children are the
scenarios that consume them, is the provisioning step. Its `create` makes it the owner of what
it builds. No new key is involved.

The test for whether the build earns a node is whether the shared thing being absent leaves a
scenario unable to run, rather than merely unconfigured. Scenarios that do not share instances
are not parented to a build node, because that would invent a dependency and serialize
independent work.

A node owns whatever its `create` brings into existence and records, not specifically an
instance. An image-building node's `create` makes something that is not an instance but
carries the identical invariant: only the owner destroys what its `create` made, teardown of
an owned artifact is post-order, and the artifact's lifetime must exceed that of the children
using it. An author who records built image names in `instance_config.yml` is using it as
designed. A node owning a non-instance artifact and shipping a reference `create`/`destroy`
example are **Proposed**.

Nothing ties a platform to the node that provides it. A child names an image, the parent built
something, and nothing connects them. The parent's `verify` is the check, so a build node
asserts in its `verify` that its artifacts exist. A child that names an image its parent never
built finds out when its own `create` fails, the same as any other bad string in a platform
selection.

An artifact is machine-global. An image tag lives in the local engine's store, visible to
every run on the host, so two concurrent runs of one project build the same tag and two
unrelated projects collide if they pick the same name. Molecule cannot make the tag unique,
because the author writes the build playbook. What Molecule owes the author is a run identity
to compose into a name for isolation, or leave out for a shared cache.

Molecule orders and gates the step, and the author writes the step. Molecule ships no
distro-aware image recipes, no registry or tag scheme or cache policy, and no `build` key on a
platform.

## The ephemeral directory

The ephemeral directory holds three kinds of content that differ in lifetime and are kept
distinct on disk rather than pooled in one flat directory.

| Category | Contents | Lifetime |
|---|---|---|
| Durable node facts | `state.yml`, `instance_config.yml`, the merged inventory | Survive between actions and between runs. The only real state |
| Materialized inputs | the resolved `molecule.yml`, `ansible.cfg` | Rewritten before every action, so never read as truth |
| Playbook scratch | whatever the author's playbooks write | Disposable at the end of the node's run |

The layout mirrors the tree, under a run, under a project segment. The project segment is
checksummed over the resolved absolute path of the project, not the directory name, so
projects that share a cache do not collide. The path is composed from explicit dimensions in
order, first the location root, then run identity, then tree position. A single-run invocation
collapses the run segment to a stable value, so ordinary usage looks unchanged.

```text
<location root>/molecule.<checksum(project,4)>/
  <run id>/                  collapses to a stable value for an ordinary single run
    vm/                      root node
      state.yml
      instance_config.yml
      inventory/
      scratch/
      install-satellite/     child node, same shape
        org-and-auth/
```

Within a run, a node's directory sits under its parent's, and contains its whole subtree. Each
segment is the node's own scenario name with `/` flattened to `--`. Removing a node removes
its descendants, which is exactly post-order teardown, and a parent's inventory outlives its
children's copies with no extra bookkeeping.

Teardown and reset name their own target. A node removes its own directory, its subtree
included, and nothing reaches upward for a parent. `molecule reset -s <node>` clears that
node's directory and its subtree, and `molecule reset` alone clears the project segment, every
run included.

## Environment and paths

A node addresses things outside itself through the environment and through locations on disk.
Both answer one question, where is the thing I need.

### Environment

Environment flows down and outward only, never between nodes. Down means Molecule computes a
node's environment fresh for every action and hands it to the process. Outward means a caller
sets variables before invoking Molecule, and Molecule maps them onto config. A node's
environment is a materialized input, rewritten before every action, and is never read back as
truth and never a channel between nodes. Facts that flow to a child travel by the snapshotted
inventory.

Caller environment is run-scoped. A variable a caller sets applies uniformly to every node in
the run, and it is not how a parent differs from a child. The way to vary one node is a
targeted run plus run-level environment, with per-node values in that node's `molecule.yml`.

Play environment rides the cascade. A node's play environment is `ansible.env`, which Molecule
hands to Ansible. It is a config key, so it cascades like any other.

| Where `ansible.env` sits | Applies to |
|---|---|
| The run's `defaults:` | every node |
| A node's `defaults:` | that node and its subtree |

Play environment reaches Ansible only, never Molecule's read of the config text. Caller input
to config text is a run arg, not an environment variable, and run args are not yet designed.

The input set is a closed, documented set rather than free-form interpolation, with precedence
defaults, then config file, then environment, then CLI. `ENV_VAR_CONFIG_MAPPING` is the home
for the mapping and gains entries, with `MOLECULE_DESTROY` for `--destroy` the first new one.

### The four path anchors

No absolute path is written into a durable artifact. Every path a user writes is relative, and
Molecule resolves it against a named anchor. cwd is never the anchor. Every path-valued config
key documents its anchor, defaulting to the scenario directory. Molecule exports every anchor
it knows.

| Anchor | Meaning | Collection | Standalone role | Playbook project |
|---|---|---|---|---|
| Scenario directory | this node's own source | always | always | always |
| Content root | the thing under test, the directory that owns the scenarios directory | the collection | the role | the project |
| Collection root | only where a collection exists | the collection | absent | absent |
| Project root | the workspace, which may hold several content roots | maybe | maybe | maybe |

Content root is the one to reach for, because the same expression resolves in a collection, a
standalone role, and a playbook project. It resolves to the nearest ancestor of the scenario
that owns a scenarios directory. Collection root resolves to the nearest ancestor holding
`galaxy.yml`, which may sit above the content root and is often absent. It is exported as
`MOLECULE_COLLECTION_DIRECTORY`, and outside a collection that variable is not defined at all
rather than defined and empty. Project root is the workspace, named by
`MOLECULE_PROJECT_DIRECTORY` when a caller sets it. The anchor variable spellings are
**Proposed**.

Discovery walks up to find the content root and resolves the scenario glob from the root it
found, so `molecule test` behaves the same from the content root and from inside a scenario
directory. The walk stops at the enclosing VCS root. `MOLECULE_GLOB` skips the walk and pins
the content root to the working directory, which is a strict non-regression for a caller who
sets it.

## Reporting

`molecule matrix` prints the tree. It already builds a structure named `tree` and hands it to
the matrix renderer, so the tree view is where a user goes to ask what the structure is, no
matter how the source is laid out.

Structural notices, such as a parent absent from a filtered run, are reported once per run,
naming the scenarios they apply to, rather than once per scenario. The same report runs from
`molecule matrix`.

The tree is reported because it teaches. Molecule states each node's parent and which
ancestors it built implicitly.

Occupancy reporting is **Proposed**: every run announces what it found standing versus what it
built, and `molecule list` gains the tree and each node's occupancy, so "what is up right now"
is one command. Reading other nodes' state for a report is the orchestrator reading, not a
node.

## Behavior in the schema, CLI as override

Any knob that changes how Molecule behaves gets a key in `molecule.yml` first, and a flag only
as an override of it. A behavior reachable only by typing a flag cannot be committed with the
project.

Precedence across the whole chain:

> CLI override then environment then the scenario's config then the built-in default.

The scenario's config tier expands to the node resolution above:

> CLI override then environment then ( bare then own defaults then ancestor defaults then run
> defaults ) then the built-in default.

A base `config.yml` discovered outside the file sits under the run `defaults:` as the outermost
configuration layer.

The distinction is behavior versus selection. Selection says what this invocation covers (`-s`,
`--exclude`, the sibling selector) and stays on the command line. Behavior says what Molecule
does with what it selected, and belongs in the file.

## Run-level lint

Run-level lint is **Proposed**. It is a lint phase that runs once per run, before any node
starts, rather than a per-node sequence action. A run with a hundred scenarios lints once. It
is not in `test_sequence`, not in any node's sequence, and not reachable per scenario.

The phase is declared in the project-level config, not in a scenario's `molecule.yml`, and is
off by default, so an existing project changes nothing while it is off. A flag can skip it but
never define it, because the CLI only overrides config. It is anchored at the content root and
runs in the run's sealed environment, so the linter version is pinned by the project's
environment, not by Molecule and not by the author's machine.

The phase is a command, not a plugin. Molecule runs the command it is told and holds no
knowledge of specific linters, and never acquires any. If lint fails, nothing in the run
starts.

## FQCN-addressable playbooks

FQCN-addressable playbooks are **Proposed** and depend on a Molecule fix that is not yet
merged (see the repository README). A scenario names a lifecycle stage playbook by collection
FQCN, for example `my_namespace.my_collection.molecule_converge`, in addition to the current
path form. This lets a shared stage playbook live under the collection's own `playbooks/` tree
and be referenced from any scenario, so it becomes ordinary collection content, linted with
the rest and addressable across scenarios.

The addition is additive by construction, because a real path never matches the FQCN shape, so
every existing path value keeps working unchanged. One caveat holds: a task's module name
cannot be Jinja-templated in Ansible, so a single shared converge that dispatches per scenario
needs a small dispatch shim to select the module. The capability removes the barrier, it does
not do the content refactor.

## Glossary

| Term | Means exactly |
|---|---|
| **Scenario** | One environment, one converge, one verify, one state, selected by name. Nothing structural |
| **Scenario tree** | A root scenario and everything declared onto it. The unit of ordering, gating, and lifetime |
| **Node** | A scenario considered as a member of a tree |
| **Root** | A node with no parent, an entry directly under `scenarios:` |
| **Parent / child** | The declared edge. A dependency, not a reference and not configuration inheritance |
| **Snapshot** | What a child starts from: a copy of the parent's inventory, owned by the child. Not a live read of the parent |
| **Gate** | The rule that a parent's verify must pass before its children start |
| **Defaults** | Configuration inheritance: the `defaults:` block and a base `config.yml`. The only mechanism called inheritance |

Further terms this page uses:

| Term | Means exactly |
|---|---|
| **Standing** | A node whose environment is up and converged, so it needs no work. Not merely created |
| **Owner** | The node whose `create` produced an object. Ownership never passes to another node |
| **Wave** | An ordering tier among siblings, roots included, with no dependency between them. Lower waves complete their subtrees before higher waves start |
| **Orchestrator** | The layer above a single scenario, which hands each node to Molecule. The only reader of other nodes' state. Never a node |
