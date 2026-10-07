# dev-sec/ansible-collection-hardening, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`ansible-collection-hardening` (pinned at commit `64a97293a230899c1584e788cdbfb486f329d649` on
`master`, copied verbatim into `before/`) and shows it collapsed into one root `molecule.yml`. The one
exception is `before/molecule/os_hardening/prepare_tasks/pw_ageing.yml`, where upstream's literal
SHA-512 password hash is replaced by one computed at run time, with a comment saying so.

The scenario folders stay because the stage playbooks stay where upstream keeps them, and Molecule
finds each scenario's `converge.yml`, `prepare.yml` and `verify.yml` by its default discovery, so the
single file names none of them. The sequences still run `verify ../shared/prerequisites.yml` exactly as upstream writes it,
relative to each scenario folder.
