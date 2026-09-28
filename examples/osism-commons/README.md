# osism.commons, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`ansible-collection-commons` (pinned at commit `baa46b2c635ab75d49a12fbe51aeae5440952144` on `main`,
copied verbatim into `before/`) and shows it collapsed into one root `molecule.yml`. The one exception is
`before/.zuul.yaml`, where upstream's five `!encrypted/pkcs1-oaep` secret values are replaced by
placeholders, with a two-line comment saying so. That makes the file 58 lines shorter than upstream's.
The counts below are upstream's.

## Changed

| | Before | After |
|---|---|---|
| Config and orchestration files | 4 | 1 |
| Scenario folders | 2 | 0 |
| Total lines | 521 | 54 |
