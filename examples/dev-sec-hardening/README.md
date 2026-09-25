# dev-sec/ansible-collection-hardening, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`ansible-collection-hardening` (pinned at commit `64a97293a230899c1584e788cdbfb486f329d649` on
`master`, copied verbatim into `before/`) and shows it collapsed into one root `molecule.yml`.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 11 | 1 |
| Scenario folders | 7 | 0 |
| Total lines | 451 | 260 |
