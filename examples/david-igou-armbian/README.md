# david_igou.armbian, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`david-igou/ansible-collection-armbian` (pinned at commit
`1a57db4eeffeed2fa2a2e6f65176955bd4ba919d` on `main`, copied verbatim into `before/`) and shows it
collapsed into one root `molecule.yml`.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 41 | 1 |
| Scenario folders | 10 | 10 |
| Total lines | 328 | 125 |

This collection had already solved the problem the other examples show. A shared
`extensions/molecule/config.yml` is deep-merged into every scenario, so each of the ten
`molecule.yml` files is four lines that declare a name and nothing else. The duplication moved one
layer down instead of going away: all ten `create.yml` are byte-identical, all ten `destroy.yml` are
byte-identical, and the ten per-scenario `inventory/` trees hold four distinct machine definitions
between them. The single-config form absorbs the inventory layer as a `platforms:` catalog of four
entries that each scenario selects by name. It does not absorb the copied `create.yml` and
`destroy.yml`, which stay in every folder.

Scenario folders do not go away. The stage playbooks stay where upstream keeps them, one set in each
scenario's own directory, and every one of them is a `<stage>.yml` that Molecule finds there by
default, so the single file names none of them. All ten folders still hold their playbooks, and the
After count is the folders that still hold a file.

The count covers the files the single file absorbs: ten `molecule.yml`, the shared `config.yml`, and
the thirty `inventory/` files. The root `Makefile` and `requirements-test.yml` survive the refactor
and are not counted, and neither are the stage playbooks, which are unchanged and stay in place.
