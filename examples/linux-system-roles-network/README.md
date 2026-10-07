# linux-system-roles/network, single-config form

This is a proof of concept of a testing layout idea. linux-system-roles/network (pinned at commit
`be29a9ffe1862ac6ba1d216488a227db34fccdf9` on `main`) uses no Molecule today. Its tests are
`tests/tests_*.yml` playbooks driven by tox-lsr, with `.fmf/` plans and an `.ostree/` path, run
against real VMs. A representative slice of that layout is copied verbatim into `before/`, and
`after/molecule.yml` declares the real `tests/tests_*.yml` playbooks, by their real repo-relative
paths, in one root file. Molecule cannot run a single root config today, so the after shows how the
layout would be authored, not a shipped setup.

Its test config is spread across `tox.ini`, `.fmf/`, `.ostree/`, `plans/` and `tests/`. The single
file declares every `tests/tests_*.yml` playbook as a scenario in one place.
