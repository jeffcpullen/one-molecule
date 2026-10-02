# Notices and attribution

Each example under `examples/` contains testing files copied from an upstream project and then
refactored into the single top-level layout. The upstream source, the exact commit the files
were taken from, and the license are listed below. Copied files keep their original license and
copyright notices, and each example's `before/` carries the upstream `LICENSE` file from the pinned
commit. Each refactored `after/molecule.yml`, and each modified upstream copy under an
`in-between/` stage, carries the license of its source in a comment header at the top of the file:
the SPDX identifier, the copyright line from the upstream license file where that file names a
holder, and a line recording that the layout was changed.

The commit column is filled in when each example is populated, so the copied state is always
traceable to an exact upstream revision.

| Example | Upstream source | Commit | License | Files copied | Change made |
|---|---|---|---|---|---|
| linux-system-roles-network | https://github.com/linux-system-roles/network | be29a9ffe1862ac6ba1d216488a227db34fccdf9 | BSD-3-Clause | test playbooks, tox / test config | refactored to single top-level `molecule.yml` |
| linux-system-roles-storage | https://github.com/linux-system-roles/storage | 75bb17d104c8e2327827d81ff5e653b84082fb57 | MIT | test playbooks, tox / test config | refactored to single top-level `molecule.yml` |
| linux-system-roles-storage (`in-between/`) | https://github.com/linux-system-roles/storage | 75bb17d104c8e2327827d81ff5e653b84082fb57 | MIT | 31 shared `tests/` playbooks and task files under `utils/playbooks/shared/`, the two `tests/scripts/` helpers under `utils/playbooks/shared/scripts/`, four `library/` modules (`find_unused_disk`, `blockdev_info`, `resolve_blockdev`, `bsize`) under `utils/playbooks/library/`, `module_utils/storage_lsr/__init__.py` and `size.py` under `utils/playbooks/module_utils/`, `tests/tests_default.yml` and `tests/tests_luks.yml` as `utils/playbooks/default.yml` and `luks.yml`, the role's runtime files (`defaults/`, `tasks/`, `vars/`, `meta/`, `library/`, `module_utils/`, `README.md`, `LICENSE`) under `roles/storage/` | role files unchanged except the COPR path, which is removed (`tasks/enable_coprs.yml` and `enable_copr.yml` deleted, their include dropped from `tasks/main-blivet.yml` and `_storage_copr_support_packages` from `vars/Fedora.yml`) because nothing sets `_storage_copr_packages`, and except `storage_use_partitions`, which `meta/argument_specs.yml` types `bool` with default `false` in place of its assert in `tasks/assert_role_vars.yml` and its null in `defaults/main.yml`, while `storage_disklabel_type` is typed `str` and `meta/main.yml` raises `min_ansible_version` to 2.11, the first release that enforces argument specs, and except the four `set_fact` tasks in `tasks/main.yml` and `tasks/main-blivet.yml` that set `_storage_pools_list` and `_storage_volumes_list` for testing, which are removed, with module names fully qualified in each changed task file, shared files, scripts, modules and module_utils unchanged except `find_unused_disk.py` and `shared/tasks/get_unused_disk.yml`, which select disks by a label on the disk serial instead of by kernel driver, and `shared/tasks/run_role_with_clear_facts.yml`, which calls the in-tree role as `storage`, resets `blivet_output` and the two lists before each role run and fills the lists from `blivet_output` after it, and has its module names fully qualified, the two converge playbooks have their include paths repointed at `shared/`, and each changed file has a licence and change header added |
| dev-sec-hardening | https://github.com/dev-sec/ansible-collection-hardening | 64a97293a230899c1584e788cdbfb486f329d649 | Apache-2.0 | `molecule/` scenarios and shared prerequisites | refactored to single top-level `molecule.yml`, and in `molecule/os_hardening/prepare_tasks/pw_ageing.yml` the literal SHA-512 password hash is replaced by one computed at run time, with a comment recording the change |
| prometheus-community | https://github.com/prometheus-community/ansible | e2f46e17d33651c3c09042aaa9c8f29b87a9753f | Apache-2.0 | per-role `molecule/` scenarios, `_common` role | refactored to single top-level `molecule.yml`, and in `roles/alertmanager/molecule/alternative/molecule.yml` the placeholder Slack webhook URL is replaced by a comment recording the change |
| arista-avd | https://github.com/aristanetworks/avd | 4d7cbccb0218d414a2cd2034b081d01b6768c487 | Apache-2.0 | `extensions/molecule/` scenarios, scenario manifest | refactored to single top-level `molecule.yml` |
| nginxinc-nginx | https://github.com/nginxinc/ansible-role-nginx | 157e0e97406f798bd6f50db37430a78c4269aa92 | Apache-2.0 | `molecule/` scenarios, `common/` build template | refactored to single top-level `molecule.yml` |
| openstack-systemd-service | https://github.com/openstack/ansible-role-systemd_service | c3c75c26c31665b0a6d09289529c6ea6d79aec61 | Apache-2.0 | `molecule/default`, shared `tests/` playbooks | refactored to single top-level `molecule.yml` |
| osism-commons | https://github.com/osism/ansible-collection-commons | baa46b2c635ab75d49a12fbe51aeae5440952144 | Apache-2.0 | `molecule/` scenarios, delegated `prepare/` tree, `.zuul.yaml` | refactored to single top-level `molecule.yml`, and in `.zuul.yaml` the five `!encrypted/pkcs1-oaep` secret values are replaced by placeholders, with a comment recording the change |
| david-igou-armbian | https://github.com/david-igou/ansible-collection-armbian | 1a57db4eeffeed2fa2a2e6f65176955bd4ba919d | MIT | `extensions/molecule/` scenarios and shared config, one `roles/` template referenced by symlink | refactored to single top-level `molecule.yml` |
| david-igou-routeros-configuration | https://github.com/david-igou/ansible-collection-routeros_configuration | 1dc714593ca8534706655fb54eb6cb5c401bd421 | MIT | `extensions/molecule/` scenarios, shared config and `utils/`, root `Makefile` | refactored to single top-level `molecule.yml`, and each line carrying a throwaway test credential has an added inline `# notsecret` comment |

`vendor/molecule.json` is the Molecule configuration schema, copied unchanged from
https://github.com/ansible/molecule at v26.6.0, commit de548442a6e43ff33bc72ea928feb0af21854362,
under the MIT license. Molecule's `LICENSE` from the same commit is beside it in `vendor/`.

Everything in this repository not covered above is original material, licensed under
Apache-2.0, copyright 2026 Jeff Pullen.
