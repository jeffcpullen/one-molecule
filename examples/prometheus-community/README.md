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
| Scenario folders | 9 | 9 |
| Total lines | 249 | 274 |

Line count does not improve here, and neither does the folder count. This repo has already factored its duplication: a shared 96-line `.config/molecule/config.yml` backs all nine scenarios, so the before side starts near its floor. What the single-config form removes is the split between a shared config and nine per-scenario overrides, not lines or folders.

The nine scenario folders stay because each still holds its testinfra test under `tests/`, which the verifier finds by its default discovery. The After folder count is the scenario folders that still hold a file, counted from upstream's tree at the pinned commit, since `before/` copies only one of those tests. The converge and prepare playbooks already live once under `.config/molecule/` upstream, and the single file names them with upstream's own strings, as it does the verifier's two `.testinfra` paths. Those strings assume Molecule's project directory is the role, as it is today. With the root file at the collection root that no longer holds, and the spec does not yet say what the project directory is for a node declared there.

The ansible-core fan-out is not in `molecule.yml`. That axis lives with the outer caller, which is what `prometheus-community/ansible` does today: its CI iterates the versions and calls the test tool as a plain caller. The per-platform `exclude_ansible_vers` stay as inventory host_vars for that caller to read.
