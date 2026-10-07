# david_igou.armbian, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`david-igou/ansible-collection-armbian` (pinned at commit
`1a57db4eeffeed2fa2a2e6f65176955bd4ba919d` on `main`, copied verbatim into `before/`) and shows it
collapsed into one root `molecule.yml`.

This collection had already solved the problem the other examples show. A shared
`extensions/molecule/config.yml` is deep-merged into every scenario, so each of the ten
`molecule.yml` files declares a name and nothing else. The duplication moved one
layer down instead of going away: all ten `create.yml` are byte-identical, all ten `destroy.yml` are
byte-identical, and the ten per-scenario `inventory/` trees hold four distinct machine definitions
between them. The single-config form absorbs the inventory layer as platform entries: a `platforms:`
catalog of three that eight scenarios select by name, and two inline entries. It does not absorb the
copied `create.yml` and `destroy.yml`, which stay in every folder.

A catalog selection's instance is named `<scenario>-<catalog name>`, but two unchanged upstream
playbooks depend on the host being named `instance`. `bootstrap_armbian/prepare.yml` reads and
rewrites `all.hosts.instance` in the runtime inventory, and `pxelinux_render/verify.yml` asserts on
`armbian/instance/`, a path the role builds from `inventory_hostname`. Those two scenarios therefore
declare an inline platform named `instance`, which keeps its name. For `pxelinux_render` that repeats
the `ubuntu-2404-podman` definition the catalog already holds. `rootfs_provision` keys its host vars
to its selection's name, `rootfs_provision-debian-13-qemu`.

The platform entries do not reach upstream's create step as they stand. Upstream's create playbook,
from `david_igou.molecule_provisioners`, reads `mp_backend`, `mp_defaults` and `mp` from the
inventory hostvars of the `molecule` group. Molecule v26.6.0 builds its inventory from each
platform's `name`, `groups` and `children` only, so each entry's `groups:` puts the instance in that
group, but its other keys reach a playbook only as `molecule_yml.platforms`, which that playbook does
not read.

Scenario folders do not go away. The stage playbooks stay where upstream keeps them, one set in each
scenario's own directory, and every one of them is a `<stage>.yml` that Molecule finds there by
default, so the single file names none of them. All ten folders still hold their playbooks.

The single file absorbs the ten `molecule.yml`, the shared `config.yml` and the `inventory/` trees.
The root `Makefile`, `requirements-test.yml` and the stage playbooks survive the refactor unchanged
and in place.
