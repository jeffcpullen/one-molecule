# linux-system-roles/storage, as-is Molecule form

The runnable middle of the three folders. `before/` is a slice of the role's current process (tox-lsr,
`.fmf` plans, `standard-inventory-qcow2`, real VMs). `after/` is the proposed single-file
`molecule.yml`, which Molecule cannot parse today. This `in-between/` is a **1-to-1 conversion into the
Molecule folder shape that ships today**: scenarios under `extensions/molecule/`, shared machinery in
`extensions/molecule/utils/`, matching the ansible-creator collection scaffold.

Everything a test needs from the role's own test tree is vendored, so the conversion is
self-contained. Each scenario's `converge` is a single playbook (`utils/playbooks/<scenario>.yml`, the
role's own `tests_<scenario>.yml`). Everything those playbooks include, the verifiers, the
`test-verify-*` chain, the `setup` / `run_role_with_clear_facts` / `get_unused_disk` task helpers and
the two helper scripts, is the shared LSR test library, vendored once under `utils/playbooks/shared/`.
The four test modules and their `module_utils` sit beside it in `utils/playbooks/library/` and
`utils/playbooks/module_utils/`. Five vendored files are edited, each with a licence and change header.
The two converge playbooks have only their include prefixes repointed at `shared/`, and their test
logic is untouched. `shared/tasks/get_unused_disk.yml` and `library/find_unused_disk.py` select disks
by label instead of by driver (see below). `shared/tasks/run_role_with_clear_facts.yml` calls the role
as `storage`.

The storage role itself is in the tree at `roles/storage/`, so it can be cut down to what is worth
keeping. Its runtime files (`defaults/`, `tasks/`, `vars/`, `meta/`, `library/`, `module_utils/`,
`README.md` and `LICENSE`) are copied from the same commit, which is ahead of the latest release,
1.22.1, and adds `meta/argument_specs.yml` and `tasks/assert_role_vars.yml`. Two cuts change them,
and each changed file carries a licence and change header:

- The COPR path is removed. Nothing sets `_storage_copr_packages`, so it never ran.
  `tasks/enable_coprs.yml` and `enable_copr.yml` are deleted, with their include in
  `tasks/main-blivet.yml` and `_storage_copr_support_packages` in `vars/Fedora.yml`.
- `storage_use_partitions` is checked by the argument spec as `type: bool`, default `false`, and its
  assert is gone. The module only tests it for truth, so null always meant false, and the spec's
  claim that null picks a layout was wrong. The other five asserts stay: the spec accepts `123` and
  `true` for a `type: str` option unchanged (ansible-core 2.21.4), and the module does not reject the
  values the size asserts reject. `storage_disklabel_type` is typed `str` but keeps its assert.

The second cut changes behaviour. An explicit `storage_use_partitions: null` from a caller now fails
validation, a string such as `"yes"` now passes where the assert rejected it, and on ansible-core 2.9
and 2.10, which the role's `min_ansible_version` still admits and which do not enforce argument specs,
the value is no longer checked at all. Upstream's `tests_invalid_input.yml` matches the assert's
message for this variable, so its two `storage_use_partitions` cases would fail against this copy.
That test is not converted here.

The upstream repository's development tooling (CI, tox, sanity ignores and its own `tests/`) is not
copied.
`config.yml` sets `ANSIBLE_ROLES_PATH` to `roles/`, so the tests run this copy and not an installed
one. The role's `library/` also carries the four test modules, unmodified. Whether the tests' disk
lookup resolves to the label-selecting copy in `utils/playbooks/library/` or to the role's copy has not
been checked by a run.

## The reuse this makes visible

A `luks` converge reaches 40 files through its includes, module calls and module imports, counted
statically with conditional branches included. 39 of them are the vendored test machinery: the 33-file
`shared/` library (the `test-verify-*` / `verify-pool-*` chain alone is 24) and the 6 module files.
They are the same `.github`-distributed files every LSR role and every one of the 51 storage test groups
pulls in, which is why they live once in `shared/` and each scenario adds only its converge on top.
Convert a second role and it reuses the same `shared/` tree rather than copying it. The
scenario-specific surface is one playbook riding on a large shared substrate.

## The lifecycle, read as objects not hosts

`create` makes the objects `converge` acts on, `destroy` removes them, `cleanup` unwinds side effects.
For storage the objects are the scenario's data disks. `create.yml` defines and boots a libvirt domain
with those disks, `converge` is the role's test playbook whose `shared/tasks/get_unused_disk.yml`
discovers them, `verify` checks exactly those labelled disks are on the node, `destroy` undefines the
domain and removes its files, and `cleanup` is a no-op because a fresh node is made per scenario.

## One ordered disk list, each scenario takes what it needs

`utils/vars/disks.yml` declares one ordered list of three scsi data disks, the scsi disks of
`before/tests/provision.fmf` with their sizes byte-for-byte: 1099511627800, 1099511627800 and
10737418240 bytes (1 TiB, 1 TiB and 10 GiB), labelled `om-scsi-0` to `om-scsi-2`. They are raw sparse
files, `format=raw`, attached through one `virtio-scsi` controller as `standard-inventory-qcow2`
(tox-lsr) attaches them, and `disks.yml` names no hypervisor.

A scenario gets the first N disks of that list. N is the inventory var `storage_test_disk_count`, which
`config.yml` sets to 1 and a scenario's `molecule.yml` overrides when its test needs a different number.
`create`, the domain template and `verify` act on that slice only, so a scenario whose test needs no
disk gets no data disk. `default` sets 0 and `luks` takes the default 1.

The number each of the 51 test groups needs, read from the disk request in its `tests_<group>.yml`:

| Disks | Test groups |
|---|---|
| 0 | default, deps, include_vars_from_parent, invalid_input |
| 2 | create_lvm_cache_then_remove, create_raid_pool_then_remove, create_raid_volume_then_remove, fatals_cache_volume, fatals_raid_pool, fatals_raid_volume, lvm_multiple_disks_multiple_volumes, null_raid_pool, swap |
| 3 | create_thinp_then_remove, raid_pool_options, raid_volume_cleanup, raid_volume_options, lvm_pool_members, stratis |
| 1 | every other group (32) |

## Disks are selected by label

Every data disk carries a label, declared in `disks.yml` and set by `create` as the disk serial. The
guest reads it back from `lsblk` SERIAL and `/dev/disk/by-id`. The label is the only way the tree finds
a data disk. The tests' disk lookup passes the selector `storage_test_disk_label`, `om-scsi-` in
`config.yml`, to `find_unused_disk`, which keeps only disks whose serial starts with it, and
`verify.yml` checks each label in the scenario's slice is on exactly one disk of the declared size and
no other disk carries a data disk label. Nothing selects on a driver, a bus or a device name.
`templates/domain.xml.j2` is the only place a disk meets a libvirt bus. A port to another hypervisor
replaces that template, keeps `disks.yml` and reproduces the labels.

## Where this diverges from upstream

- **One disk class.** Upstream provisions nine disks (three virtio, three scsi, three nvme) and ships
  each test group as three playbooks: the base playbook and the generated `_scsi` and `_nvme` variants. No
  role or assertion code branches on the class. `find_unused_disk` returns device names sorted, so on
  that layout a base or `_scsi` run asking for three disks or fewer takes `sda`, `sdb`, `sdc` in that
  order, which is this list. Here each group runs once, against scsi disks.
- **No nvme coverage.** The only nvme-specific code on the path is blivet's NVMe device population,
  which runs only when an nvme disk exists. Upstream CI never makes one: Testing Farm attaches every
  drive as a SCSI LUN and skips the nvme tests, and the GitHub Actions qemu job skips them too.
- **lvm_pool_members and stratis get three disks where upstream base got six.** Both take every
  qualifying disk as the pool, and a base run on the `provision.fmf` layout qualifies its three scsi and three virtio disks.
  Here they get three, as upstream's `_scsi` variant does.
- **Selection by label, not driver.** Upstream's `find_unused_disk` takes `with_interface` and
  substring-matches it against the disk's kernel driver path, so `virtio` also matches the scsi disks,
  whose driver is `virtio_scsi`. Here it takes `with_label` and matches the serial, and the `null_blk`
  name filter goes with the driver match. Upstream's generated variants set
  `storage_test_use_interface`, and here the selector is `storage_test_disk_label`.

## Folder shape

```
in-between/
  galaxy.yml                            collection root, without which config.yml is never loaded
  roles/
    storage/                            the role under test, upstream runtime files with two cuts
  extensions/
    molecule/
      config.yml                        auto-loaded base config: dependency, driver, env, vars, playbooks
      requirements.yml                  collections, for the dependency step
      utils/
        playbooks/
          create.yml                    make the domain + the scenario's labelled disks
          verify.yml                    check exactly those labels are on the node
          destroy.yml                   remove them
          cleanup.yml                   no-op (ephemeral node)
          default.yml                   default scenario converge (role's tests_default.yml)
          luks.yml                      luks scenario converge (role's tests_luks.yml)
          shared/                       the LSR test library, vendored once (33 files)
            verify-role-results.yml  verify-role-failed.yml  verify-data-preservation.yml
            create-test-file.yml
            test-verify-*.yml  verify-pool-*.yml     (the verify chain, 24 files)
            tasks/
              setup.yml  run_role_with_clear_facts.yml  get_unused_disk.yml
            scripts/
              does_library_support.py  stratis_pool_info.py
          library/                      find_unused_disk (selects by label), blockdev_info,
                                        resolve_blockdev, bsize
          module_utils/storage_lsr/     __init__.py, size.py
          templates/
            domain.xml.j2               disk -> scsi bus, label -> disk serial
            user-data.j2                cloud-init NoCloud
        vars/
          disks.yml                     the ordered three-disk scsi list and its labels
          hypervisor.yml                libvirt URI, network, domain and work dir names
      default/molecule.yml              converge: ../utils/playbooks/default.yml, 0 disks
      luks/molecule.yml                 converge: ../utils/playbooks/luks.yml
```

The scaffold reference is ansible-creator's collection template: scenarios at
`extensions/molecule/<scenario>/molecule.yml`, shared playbooks at
`extensions/molecule/utils/playbooks/`, shared vars at `extensions/molecule/utils/vars/`.

Molecule auto-loads a base config from `extensions/molecule/config.yml` and deep-merges each scenario's
`molecule.yml` on top, with no `--base-config` flag. It does that only inside a collection, which is why
this tree carries a `galaxy.yml`. With no collection root the search finds nothing, and because a
missing playbook is a warning rather than an error, `molecule create` then exits 0 having created
nothing. So the shared blocks (dependency, driver, env, vars, create/destroy/cleanup/verify) live in
`config.yml` once and a scenario file is its `converge` plus, where it differs from 1, its disk count.
Those two knobs are what vary across the 51 test groups, and the `after/` single-file form carries both
in one list.

## Running it

Run Molecule from this directory, for example `molecule test -s luks`. The collection is detected from a
`galaxy.yml` in the current working directory only, so run from anywhere else and the base config is
never loaded. The auto-load needs molecule 25.9.0 or later. A `.config/molecule/config.yml` at the root
of the enclosing git checkout takes precedence over it, and this repository has none.

The scenarios need a libvirt host with an active network named `default`, and a controller with the
libvirt client (`virsh`) and its Python bindings, `lxml`, `qemu-img` and `cloud-localds`. The
collections and the role are installed by the dependency step. Point `MOLECULE_BASE_IMAGE` at a cloud
qcow2 image whose cloud user is `cloud-user` (the default path is a Fedora cloud base image).
`LIBVIRT_DEFAULT_URI` defaults to `qemu:///system`. The ephemeral directory holds the disks, so it must
be traversable by the user the hypervisor runs qemu as. Relocate it with `MOLECULE_EPHEMERAL_DIRECTORY`
if it is not.

## Changed

| | Before | In-between |
|---|---|---|
| Disk provisioning | provision.fmf via standard-inventory-qcow2, nine disks in three classes for every run | utils/playbooks/create.yml + domain.xml.j2, the first N of the three scsi disks, each labelled |
| Disk selection | find_unused_disk matches the kernel driver (with_interface) | find_unused_disk matches the label on the disk serial (with_label) |
| Shared config | .github-managed vars, harness env | extensions/molecule/config.yml (auto-loaded once) |
| Molecule lifecycle | tox-lsr, .fmf plans | utils/playbooks/ (create/verify/destroy/cleanup once) |
| Test library | injected per role from .github | utils/playbooks/shared/ (vendored once, 33 files) plus 6 module files |
| Per-scenario file | tox-lsr conventions, .fmf plans | one converge playbook, everything else shared |
| Scenarios | 51 distinct test groups (151 playbooks, base plus scsi and nvme variants of 50 of them) | 2 scenario dirs under extensions/molecule, one per vendored test, scsi only |

## Caveats

Only 2 of the 51 test groups are converted, the two whose test playbooks are vendored in `before/`.
The other 49 are not here. Both converted scenarios passed a full `molecule test` against a libvirt
host at release 1.22.1, with the role installed from Galaxy. They have not been rerun since the move to
this commit and the in-tree role. The default test sequence runs without `idempotence` and
`side_effect`, because the LSR test playbooks create and remove volumes and provoke role failures on
purpose. The vendored files are byte-for-byte upstream (storage at
`75bb17d104c8e2327827d81ff5e653b84082fb57` on `main`) except five test files, and the role under
`roles/storage/` is too except for the two cuts described above. The two converge
playbooks have only their include prefixes and a licence and change header changed.
`find_unused_disk.py` and `get_unused_disk.yml` select by label, as described above.
`run_role_with_clear_facts.yml` names the in-tree role. Each scenario runs once against scsi disks,
so the nvme coverage upstream's `_nvme` variants carry is not reproduced here. `default` creates no
data disk. `luks` creates one, `om-scsi-0`, and its disk lookup takes it as `sda`.
