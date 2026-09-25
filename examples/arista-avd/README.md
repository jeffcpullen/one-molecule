# arista.avd, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`arista.avd` (pinned at commit `4d7cbccb0218d414a2cd2034b081d01b6768c487` on `devel`, copied verbatim
into `before/`) and shows it collapsed into one root `molecule.yml`.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 32 | 1 |
| Scenario folders | 30 | 0 |
| Total lines | 914 | 342 |

The version fan-out (controller python and ansible-core) is not in `molecule.yml`. That axis lives with the outer caller, which is what `arista.avd` does today: its CI iterates the versions and calls the test tool as a plain caller. The single-config form carries the tree, the outer caller carries the grid.
