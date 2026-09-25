# prometheus-community/ansible, single-config form

This is a proof of concept of a testing layout idea. It takes a representative subset of the real
molecule scenario set from `prometheus-community/ansible` (pinned at commit
`e2f46e17d33651c3c09042aaa9c8f29b87a9753f` on `main`, the `node_exporter`, `alertmanager` and
`apache_exporter` roles' `default`, `alternative` and `latest` scenarios, copied verbatim into
`before/`) and shows it collapsed into one root `molecule.yml`. The one exception is the
alertmanager `alternative` scenario, where upstream's placeholder Slack webhook URL is replaced by
a one-line comment saying so, in `before/` and `after/` alike.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 11 | 1 |
| Scenario folders | 9 | 0 |
| Total lines | 249 | 274 |

Line count is the one metric that does not improve here, and the reason is that this repo has already factored its duplication: a shared 96-line `.config/molecule/config.yml` backs all nine scenarios, so the before side starts near its floor. What the single-config form removes is the nine scenario folders and the split between a shared config and nine per-scenario overrides, not lines.

The ansible-core fan-out is not in `molecule.yml`. That axis lives with the outer caller, which is what `prometheus-community/ansible` does today: its CI iterates the versions and calls the test tool as a plain caller. The per-platform `exclude_ansible_vers` stay as inventory host_vars for that caller to read.
