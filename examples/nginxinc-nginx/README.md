# nginx/ansible-role-nginx, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`nginx/ansible-role-nginx` (pinned at commit `157e0e97406f798bd6f50db37430a78c4269aa92` on `main`, copied
verbatim into `before/`) and shows it collapsed into one root `molecule.yml`.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 15 | 1 |
| Scenario folders | 14 | 0 |
| Total lines | 3042 | 866 |
