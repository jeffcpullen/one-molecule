# dev-sec/ansible-collection-hardening, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`ansible-collection-hardening` (pinned at commit `64a97293a230899c1584e788cdbfb486f329d649` on
`master`, copied verbatim into `before/`) and shows it collapsed into one root `molecule.yml`. The one
exception is `before/molecule/os_hardening/prepare_tasks/pw_ageing.yml`, where upstream's literal
SHA-512 password hash is replaced by one computed at run time, with a comment saying so. That file is
not among the counted ones.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 11 | 1 |
| Scenario folders | 7 | 0 |
| Total lines | 451 | 260 |

Six sequences in the single file still run `verify molecule/shared/prerequisites.yml`, upstream's
path. That playbook is named as the argument to a `verify` step inside a sequence rather than under
`playbooks:`, and this example does not assume the collection FQCN reference form reaches step
arguments. Moved into `playbooks/molecule/` as the shared-folder recipe describes, those six
references would name the new path instead.
