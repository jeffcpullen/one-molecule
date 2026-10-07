# openstack/ansible-role-systemd_service, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario from
`ansible-role-systemd_service` (pinned at commit `c3c75c26c31665b0a6d09289529c6ea6d79aec61` on
`master`, copied verbatim into `before/`) and shows it collapsed into one root `molecule.yml`.

The `default` folder held only its `molecule.yml`, so it goes. The converge, side effect and verify
playbooks it pulls from `tests/` stay there, and the single file names them by the paths upstream
wrote.
