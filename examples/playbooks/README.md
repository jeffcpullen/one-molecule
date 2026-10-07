# Two playbooks, single-config form

This is a synthetic example, written for this repo. It is a playbook project with two playbooks,
`playbooks/motd.yml` and `playbooks/hosts.yml`, each tested by its own Molecule scenario, and every
scenario declared in one root `molecule.yml`.

The scenarios share config only. Each one targets localhost and writes to its own ephemeral
directory, so neither needs the other to run. The driver, the platform, the connection settings, the
verifier and the test sequence therefore sit once under `defaults:`, and the two scenarios stay
independent roots. Each node carries only the path its playbook writes to, which deep-merges into
the shared inventory variables.

Nothing moves to `playbooks/molecule/`, because nothing is shared. Each scenario's `converge.yml`
imports a different playbook and each `verify.yml` checks a different file, so both stay in the
scenario's own folder under `molecule/`, where Molecule finds them by default discovery.

Today's layout would carry a full `molecule.yml` in each scenario folder, the two differing only in
the one path variable. The converter does not project this example yet, because it offers only the
collection layout (`extensions/molecule/`) and this project keeps its scenarios in a top-level
`molecule/`.
