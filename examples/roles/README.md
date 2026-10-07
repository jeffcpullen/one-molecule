# Three roles, single-config form

This is a synthetic example, written for this repo. It is a repository of three standalone roles,
`motd`, `issue` and `profile`, each tested by its own Molecule scenario, and every scenario declared
in one root `molecule.yml` at the repository root.

Today each role would carry its own `roles/<role>/molecule/default/` folder with a `molecule.yml`, a
`converge.yml` and a `verify.yml`. Here the roles carry no test folders. The scenarios are named for
their roles and live in one top-level `molecule/` directory, and each keeps only its `verify.yml`,
because what it checks is particular to its role.

The three roles are independent, so they stay roots and share their config through `defaults:`. The
three converge playbooks would have been the same play applying a different role, so they fold onto
one shared `playbooks/molecule/converge.yml` that applies the role each node names in
`role_under_test`. That fold is an author-side refactor that the shared folder makes possible, not
something the conversion does on its own.

With the scenarios outside the roles, `defaults:` sets `ANSIBLE_ROLES_PATH` to the project's `roles/`
folder, so the shared converge finds each role by its short name.

The converter does not project this example yet, because it offers only the collection layout
(`extensions/molecule/`).
