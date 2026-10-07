# osism.commons, single-config form

This is a proof of concept of a testing layout idea. It takes the real molecule scenario set from
`ansible-collection-commons` (pinned at commit `baa46b2c635ab75d49a12fbe51aeae5440952144` on `main`,
copied verbatim into `before/`) and shows it collapsed into one root `molecule.yml`. The one exception is
`before/.zuul.yaml`, where upstream's five `!encrypted/pkcs1-oaep` secret values are replaced by
placeholders, with a two-line comment saying so.

The `delegated` scenario folder stays because its stage playbooks and test files stay where upstream
keeps them, and Molecule finds its `converge.yml` and `prepare.yml` by its default discovery, so the
single file names neither. The `default`
folder held only its `molecule.yml`, so it goes.
