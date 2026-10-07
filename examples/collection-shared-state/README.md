# example.shared_state, single-config form

This is a synthetic example, written for this repo. It is a collection scaffolded with
ansible-creator 26.9.0 and given two roles, `app_config` and `app_users`, that both write into one
installed application tree on one host. One scenario stands that host and tree up and two
scenarios test the roles against it, all declared in one root `molecule.yml`. Only `galaxy.yml`,
`meta/runtime.yml`, the roles, the root file and `playbooks/molecule/` are kept, and `galaxy.yml`
names Apache-2.0.

Today this needs `shared_state: true` in a shared `extensions/molecule/config.yml`. Molecule then
runs the `default` scenario's `create` and `destroy` once around the whole suite, and the other
scenarios reuse what it built. The scenario that owns the environment has to be called `default`,
and nothing in the files says which scenarios depend on it.

Here `default` is a root and the two role scenarios are its children, so the nesting says what
`shared_state` said and the key is gone. `default`'s create starts the container and then lays out
`/opt/app/etc` and `/opt/app/data`, which the roles write into. Without that host and tree a role
scenario cannot run at all, which is what makes `default` a parent rather than shared `defaults:`.

The shared stages are written once under `defaults:`. `create.yml` and
`destroy.yml` start and remove the selected platforms with the `podman` CLI, and `converge.yml` is
a single `include_role` on `example.shared_state.` plus the scenario name, read from
`MOLECULE_SCENARIO_NAME`. `default` names its own `create-default.yml`, which imports the shared
create and adds the tree, and its sequence of create, verify and destroy never runs converge.
Each node names its own `verify-<scenario>.yml`. The children select no platforms, so they test
against the parent's container. They inherit `create` and `destroy` from `defaults:` too, but
under `shared_state` Molecule runs those two stages only for `default`.

The platform image is `quay.io/fedora/fedora-toolbox:42` because the plain Fedora images carry no
Python. The `containers.podman` collection is needed for its connection plugin only.

The converter maps this tree onto today's form. It writes `config.yml` with `shared_state: true`,
and gives each child the parent's `default-instance` platform entry, so the child's inventory
holds the parent's host. A tree of any other shape, such as a root not named `default` or a
grandchild, cannot be expressed with `shared_state`, and the converter reports why.

That projection, placed in a copy of this folder at `ansible_collections/example/shared_state/`,
passed `molecule test --all` on Molecule 26.9.0, ansible-core 2.21.4 and containers.podman 1.21.0
against rootless podman 5.6.2. Both roles were applied to `default-instance` and verified, then
`default` verified the tree and destroyed the container. It is a preset on the converter page.

The two children write different files, so they are safe to run side by side. Both run on one
container, though, so a role that changed state the other reads would make their order matter,
and nothing here guards against that.
