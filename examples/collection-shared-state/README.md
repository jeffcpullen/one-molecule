# example.shared_state, single-config form

This is a synthetic example, written for this repo. It is a collection scaffolded with
ansible-creator 26.9.0 and given two roles, `app_config` and `app_users`, that both write into one
installed application tree. One scenario stands that tree up and two scenarios test the roles against
it, all declared in one root `molecule.yml`. Only `galaxy.yml`, `meta/runtime.yml`, the roles and the
Molecule tree are kept from the scaffold, and `galaxy.yml` names Apache-2.0.

Today this needs `shared_state: true` in a shared `extensions/molecule/config.yml`. Molecule then runs
the `default` scenario's `create` and `destroy` once around the whole suite, and the other scenarios
reuse what it built. The scenario that owns the environment has to be called `default`, and nothing in
the files says which scenarios depend on it.

Here `default` is a root and the two role scenarios are its children, so the nesting says what
`shared_state` said and the key is gone. The roles write into `etc/` and `data/`, which only
`default`'s `create.yml` makes. Without that tree a role scenario cannot run at all, which is what
makes `default` a parent rather than shared `defaults:`. The tree's location is different: every
scenario only needs to know it, so `app_root` is an inventory variable under `defaults:`. The children
leave `create` unset and have no `create.yml`, so they own nothing and test against the parent's tree.
The shared `noop.yml` for `prepare` and `cleanup` lives in `playbooks/molecule/`.

The two children write different files, so they are safe to run side by side. `app_root` is a fixed
path under the temporary directory, though, so two runs of the whole project on one machine would
share and remove the same tree.

The converter projects this file into per-scenario files and reports each child's parent edge as
lost, because today's Molecule cannot express it outside `shared_state`. It is a preset on the
converter page.
