# openstack/ansible-role-systemd_service, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario from
`ansible-role-systemd_service` (pinned at commit `c3c75c26c31665b0a6d09289529c6ea6d79aec61` on
`master`, copied verbatim into `before/`) and shows it collapsed into one root `molecule.yml`.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 4 | 1 |
| Scenario folders | 1 | 0 |
| Total lines | 151 | 44 |
