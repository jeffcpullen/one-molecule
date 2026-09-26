# Why one layout is easier for the person writing the tests

This page is about the author writing Molecule tests, and why declaring scenarios as a tree
in one root config is less work than the per-scenario directory layout in use today. It is
the reasoning behind the pattern, which is proposed design for Molecule and not current
behavior. For the authoring surface see [the pattern](the-pattern.md), for the full
specification see the [reference](reference.md), to build a tree from nothing see
[getting started](getting-started.md), and to convert an existing project see
[migrating](migrating.md).

## The problem: shared setup has nowhere to live

Molecule's only scope larger than a single scenario is the whole run. A scenario is one
environment, one converge, one verify, one state. Above that there is nothing until you reach
the entire invocation. So the moment two scenarios need to share something, whether that is a
converge playbook, a verify playbook, a driver block, or an environment they both test
against, there is no place in Molecule's model to put it.

The author still has to put it somewhere, so the shared material ends up copied into each
scenario directory, symlinked between them, or pulled in through a small shim playbook. Each
of those answers the same missing scope, and every project reaches for a different one.

The variety is the symptom. Across a handful of community projects, the same job, sharing
setup across scenarios, is solved at least seven different ways: a project-local `../shared/`
directory, a `_common` role, a `common/` Dockerfile shim, playbooks pulled from a separate
`tests/` tree, a large delegated `prepare/` tree, and more. The full table is in the
repository README. When one need produces that many layouts, the need has no
home, and each author has spent time inventing one.

## The idea: declare scenarios as a tree

Instead of one directory per scenario, the author declares the scenarios as a tree in a
single `molecule.yml` at the project root. Each scenario is a named node in that file rather
than a directory on disk. The root config carries the run-level defaults, the scenario
declarations, and the edges between them.

Declaring a scenario as a named entry in the root file is a second discovery mode alongside
today's directory globbing, not a replacement. Existing projects keep their scenario
directories and still run unchanged, and a new project may declare its scenarios flat in the
root file. Only the root file declares a tree. A scenario in its own directory has no edge.

Shared playbooks are written once, under `playbooks/molecule/`, and each scenario references
the ones it needs by name. Molecule already references playbooks by path through its
`provisioner.playbooks` mapping, so referencing is not a new mechanism. What is new is that
several scenarios can name the same file, so shared content is written once and read by many,
with no copy.

The edges between nodes are dependencies. A parent scenario builds and verifies an
environment that its children depend on, and the parent's verify is the readiness gate: a
child does not start until its parent has verified. When a child starts, it begins from a
snapshot of its parent, so the environment the parent stood up is there for the child to test
against.

One construct covers both shapes an author needs. A chain of nodes, parent to child to
grandchild, is an ordered pipeline, where each step depends on the one before it. A set of
nodes that all hang off the same parent, or that declare no parent at all, are independent
tests that share only what the parent provides. The same tree declaration expresses a
pipeline, a fan-out, or a mix of the two.

## Why the tree is easier for the author

Shared content is written once and referenced, never copied. A converge or verify playbook
that several scenarios use lives in one file under `playbooks/molecule/`. There is nothing to
keep in sync across directories, no symlink to maintain, and no shim playbook standing in for
a home that did not exist. Because these playbooks sit under the project's own `playbooks/`
tree, they are ordinary content: addressable by name and linted like any other playbook.

The whole test structure is visible in one file. The scenarios, and which one depends on
which, are declared together in the root `molecule.yml` rather than spread across directories
whose relationships you have to reconstruct by reading each one. When the author wants the
structure rendered, `molecule matrix` prints the tree, so there is an at-a-glance view no
matter how the source is laid out.

Selecting one scenario pulls in what it depends on, automatically. A request for a node is a
request for the node and its ancestors, because a child cannot run without the parent that
builds its environment. The author selects the scenario they care about and the setup it
needs comes along with it, in order. There is no separate step to remember to run the parent
first, and no filtered run that quietly tests nothing because the setup was left out.
Selection narrows what is tested, never what is depended on.

Put together, the author stops hand-managing setup order and stops maintaining copies. The
dependency is declared once, and Molecule follows it.

## When you need a parent, and when you only need shared config

A parent node is for a dependency, not for shared configuration, and the two are easy to tell
apart with one question: if the shared thing were absent, would the scenario be unable to run,
or merely unconfigured?

Unable to run is a dependency, and it wants a parent. An image the scenario needs, a template
it deploys from, a server it tests against: without those, there is no run, so the thing that
builds them is a parent and its verify is the gate.

Merely unconfigured is not a dependency. Independent scenarios that happen to share playbook
paths, a driver block, or a test sequence are not depending on each other, they are just
repeating configuration. That is what base configuration is for. Molecule already loads a base
config and merges each scenario on top of it, so shared settings belong there. Parenting
independent scenarios to a shared node to save that repetition invents a dependency that is
not real: it serializes scenarios that could run on their own, and it skips all of them when
the shared node fails.

Use the tree for what one scenario genuinely needs another to build. Use base configuration
for settings that several scenarios merely repeat.

## What happens to `shared_state`

Molecule has one setting today that expresses a set of related scenarios, `shared_state`. It
ties a run's scenarios to a scenario named `default` that stands up an environment they all
test against. That is the second scope carried in the run-wide layer, because there was no
tree to declare it on.

Under this design `shared_state` keeps Molecule's own meaning. A project that stays in its
scenario directories runs exactly as it does today, `shared_state` included, with no
deprecation and no alias. No existing behavior changes. `shared_state` is not a key in the
single root file, because there the relationship it stood in for is declared directly, by
nesting the scenarios that test against an environment under the node that stands it up.

The deeper change is that state becomes per-node for a tree. Each node reads and writes only
its own state, and there is no shared state file. Nothing is shared between sibling nodes, so
running them in parallel does not race over one directory. The safety is by construction,
because there is nothing shared left to make safe. For converting a `shared_state` project to
a tree, see recipe 1 in [migrating](migrating.md).

## What it looks like on a real project

The upstream [`ansible/ansible.platform`](https://github.com/ansible/ansible.platform)
collection is the clearest case, because it uses Molecule's existing `shared_state` setting,
where one scenario stands up a mock server and every other scenario tests against it. In its
current layout that is 23 scenario directories under `extensions/molecule/`, 97 files in all:
a shared base config, a `default` scenario that runs create and destroy, and 22 mock
scenarios, each with its own `molecule.yml` and its own converge, verify, and cleanup
playbooks.

Expressed as a tree, `default` becomes the root that owns the mock server and the 22 mocks
become its children. Ownership is derived, not declared with a flag. `default` owns the
instances because it is the node that references a `create` playbook, and the mocks reference
none, so they own nothing and start from a snapshot of `default`. The shared base config and
the per-scenario `molecule.yml` files would collapse into the single root config, and the
shared playbooks would move once into `playbooks/molecule/`.

The collapse has two parts.

The config collapse is automatic. Turning `shared_state` into a tree, moving the repeated
driver, platforms, verifier, and environment settings into one root `defaults:` block, and
letting the tree snapshot the inventory down to the children removes the per-scenario
`molecule.yml` files directly. That is what declaring the tree does for you.

The further collapse of the playbooks is an author-side content refactor that the shared
folder makes possible, not something Molecule does for you. Most of the 22 mocks run the same
converge, verify, and cleanup skeleton, differing mainly in which module they call and a few
variables. Once there is a shared `playbooks/molecule/` folder to hold one copy, the author
can fold those mocks onto a single shared playbook trio parameterized per child, and keep
separate playbooks only for the few that genuinely diverge. Molecule gives the shared content
a home, the author does the deduplication.

## Where to go next

For how the root `molecule.yml` is structured, how playbooks are referenced, and why the
project root is the home for the config, read [the pattern](the-pattern.md). For every key and
behavior, read the [reference](reference.md). To build a tree step by step, read
[getting started](getting-started.md).
