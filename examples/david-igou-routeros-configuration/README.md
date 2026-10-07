# david_igou.routeros_configuration, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`david-igou/ansible-collection-routeros_configuration` (pinned at commit
`1dc714593ca8534706655fb54eb6cb5c401bd421` on `main`, copied verbatim into `before/`) and shows it
collapsed into one root `molecule.yml`. The one exception is that each line carrying a throwaway test
credential has an added inline `# notsecret` comment, which adds no lines.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 25 | 1 |
| Scenario folders | 22 | 22 |
| Total lines | 331 | 193 |

This example is evidence for translating `shared_state`, not for nesting. `extensions/molecule/config.yml`
sets `shared_state: true` for the whole suite, `default` boots one MikroTik CHR and owns create,
prepare and destroy, and twenty scenarios converge against that one device. In the single file
`default` is a root and the twenty are its children, so the nesting says what `shared_state` said and
the key is gone. Molecule runs this shape today. The tree is one level deep, and nothing here needs a
parent below a parent or any relationship `shared_state` cannot already express. `lifecycle` sets
`shared_state: false` upstream and boots its own CHR, so here it is a second root. Both roots boot the
same machine definition, which upstream keeps as one static `utils/inventory/` tree and which becomes
a `platforms:` catalog of one entry. Each root selects it, so the two instances are `default-chr-1`
and `lifecycle-chr-1`, and no upstream playbook names the host.

The catalog entry does not reach upstream's create step as it stands. Upstream's create playbook,
from `david_igou.molecule_provisioners`, reads `mp_backend`, `mp_defaults` and `mp` from the
inventory hostvars of the `molecule` group. Molecule v26.6.0 builds its inventory from each
platform's `name`, `groups` and `children` only, so the entry's `groups:` puts the instance in that
group, but its other keys reach a playbook only as `molecule_yml.platforms`, which that playbook does
not read.

The line drop is comments, not structure. Not counting blank lines, comments and `---` markers, the 25
files hold 175 lines and the single file holds 186, so on content the single file is 11 lines longer.
The ordering below adds 19 `wave:` lines.

The scenario folders stay. Each still holds its stage playbooks where upstream keeps them, and
Molecule finds `converge.yml` and `verify.yml` there by its default discovery, so no scenario names
them. The After count is the folders that still hold a file once their `molecule.yml` is gone, which
is all 22. The two roots name upstream's shared `create`, `prepare` and `destroy` playbooks by the
same `../utils/playbooks/` paths upstream's `config.yml` uses, resolved against each scenario's own
directory.

Upstream's `Makefile` runs the twenty one at a time and says the order matters: `ping` and `fetch` run
before `configure_full` installs a firewall that drops ICMP and HTTP, and `restore` and `reboot` run
last so their reboots cannot race another converge. Here `wave:` declares that order. `ping` and
`fetch` are in wave 0, the other sixteen in wave 1, `restore` in wave 2 and `reboot` in wave 3.
`negative` is validation-only and the `Makefile` says it is safe anywhere, so it sits in wave 1 rather
than after `reboot` where upstream lists it. Waves do not make wave 1 safe to run concurrently. Its
sixteen scenarios share one device, and `configure_singletons`, `configure_full` and `reset` each set
its system identity to a different value, so the file is correct only under `--workers 1`, which runs
wave 1 in list order. `lifecycle` is in root wave 1 because it forwards the same host ports, 8728 and
2223, as `default`, so it starts only after the whole `default` tree has finished and destroyed its
CHR. Upstream gets the same effect by running it as a separate `molecule test -s lifecycle`.

The count covers the files the single file absorbs: 22 `molecule.yml`, the shared `config.yml`, and
the two `utils/inventory/` files. The `Makefile` is not counted and survives for install and build,
though two of its jobs would pass to the tree: prepending `default` to a single-scenario run is
ancestor closure, and the guard that fails CI on an unlisted scenario has nothing to guard when the
file is the list. Also not counted: `requirements-test.yml` and the stage playbooks, including the
`utils/playbooks/` ones, which are unchanged and stay where upstream keeps them.
