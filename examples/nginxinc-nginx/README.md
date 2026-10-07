# nginx/ansible-role-nginx, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`nginx/ansible-role-nginx` (pinned at commit `157e0e97406f798bd6f50db37430a78c4269aa92` on `main`, copied
verbatim into `before/`) and shows it collapsed into one root `molecule.yml`.

The fourteen scenario folders stay because each still holds its stage playbooks, a converge and a verify in every one and a prepare or cleanup in some. Molecule finds them by its default discovery, so the single file names none of them. `before/` copies only some of those playbooks. The shared `Dockerfile.j2` keeps upstream's `../common/` path, relative to the scenario directory.

Most of the single file is platform lists. Three scenarios run a platform set one entry short of the default 24, and a list replaces rather than merges, so each restates its other 23 entries in full.
