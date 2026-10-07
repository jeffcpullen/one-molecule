"""Project a single-config molecule.yml into today's per-scenario file tree.

Standard library only. Key classes come from the schema's `x-class` annotations.
"""

PLAYBOOKS_ALIAS = "playbooks"
PROVISIONER = "provisioner"
PLATFORMS = "platforms"
CHILDREN = "children"
WAVE = "wave"
NAME = "name"
DEFAULTS = "defaults"
SCENARIOS = "scenarios"
SCENARIO_ROOT = "molecule"
SCENARIO_FILE = "molecule.yml"


class KeyClasses:
    """Key classes for the run level and a node, read from the schema."""

    def __init__(self, schema):
        """Read the run and node key classes.

        Args:
            schema: the config schema as a dict (generated JSON form).
        """
        self.run = {k: p.get("x-class") for k, p in schema["properties"].items()}
        node = schema["definitions"]["node"]["properties"]
        self.node = {k: p.get("x-class") for k, p in node.items()}
        self.config_order = [k for k, c in self.node.items() if c == "config"]

    def is_config(self, key):
        """Return True when a node key is a config key."""
        return self.node.get(key) == "config"


def _notice(kind, node, key, message):
    return {"kind": kind, "node": node, "key": key, "message": message}


def _is_empty(value):
    return value is None or value == ""


def deep_merge(lower, higher):
    """Merge `higher` over `lower`. Mappings merge by key, anything else replaces.

    Args:
        lower: the lower precedence layer.
        higher: the higher precedence layer.

    Returns:
        A new merged value. Inputs are not modified.
    """
    if isinstance(lower, dict) and isinstance(higher, dict):
        merged = dict(lower)
        for key, value in higher.items():
            merged[key] = deep_merge(lower[key], value) if key in lower else _copy(value)
        return merged
    return _copy(higher)


def _copy(value):
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy(v) for v in value]
    return value


def drop_empty(value):
    """Remove every mapping key whose value is empty (null or the empty string).

    Args:
        value: a resolved config value.

    Returns:
        The value with empty mapping entries removed, recursively through mappings.
    """
    if isinstance(value, dict):
        return {k: drop_empty(v) for k, v in value.items() if not _is_empty(v)}
    return value


def fold_playbooks_alias(layer, node_name, notices):
    """Move a layer's `playbooks` alias into `provisioner.playbooks`.

    Args:
        layer: one config layer (run defaults or a node's bare keys).
        node_name: the node the layer belongs to, or None for run defaults.
        notices: list that receives an error notice on a conflicting stage.

    Returns:
        A new layer without the alias key.
    """
    if PLAYBOOKS_ALIAS not in layer:
        return layer
    layer = _copy(layer)
    alias = layer.pop(PLAYBOOKS_ALIAS)
    provisioner = layer.get(PROVISIONER)
    if provisioner is None:
        provisioner = {}
    existing = provisioner.get("playbooks") or {}
    clash = sorted(set(existing) & set(alias or {}))
    if clash:
        notices.append(_notice(
            "error", node_name, "playbooks",
            "Stage set both through `playbooks` and `provisioner.playbooks` in one layer: "
            + ", ".join(clash) + ". The spec names no winner."))
    provisioner = dict(provisioner)
    provisioner["playbooks"] = deep_merge(alias or {}, existing)
    layer[PROVISIONER] = provisioner
    return layer


def _config_layer(mapping, classes):
    return {k: v for k, v in mapping.items() if classes.is_config(k)}


def _ordered(resolved, classes):
    out = {}
    for key in classes.config_order:
        if key in resolved:
            out[key] = resolved[key]
    for key, value in resolved.items():
        if key not in out:
            out[key] = value
    return out


def _playbook_paths(resolved):
    playbooks = (resolved.get(PROVISIONER) or {}).get("playbooks") or {}
    return [(stage, path) for stage, path in playbooks.items() if isinstance(path, str)]


def _check_keys(mapping, allowed, where, notices):
    for key in mapping:
        if key not in allowed:
            notices.append(_notice("error", where, key, f"`{key}` is not a key the spec declares here."))


def project(config, schema):
    """Project a single-config molecule.yml into per-scenario files.

    Args:
        config: the parsed single-config molecule.yml.
        schema: the config schema as a dict (generated JSON form).

    Returns:
        A dict with `files`, a list of {path, content} in tree pre-order, and
        `notices`, a list of {kind, node, key, message} where kind is `error`,
        `unresolved` or `lost`.
    """
    classes = KeyClasses(schema)
    notices = []
    files = []

    if not isinstance(config, dict):
        notices.append(_notice("error", None, None, "The file is not a mapping."))
        return {"files": files, "notices": notices}
    _check_keys(config, classes.run, None, notices)

    catalog = config.get(PLATFORMS) or []
    run_defaults = config.get(DEFAULTS) or {}
    if not isinstance(run_defaults, dict):
        notices.append(_notice("error", None, DEFAULTS, "`defaults` is not a mapping."))
        run_defaults = {}
    _check_keys(run_defaults, classes.config_order, DEFAULTS, notices)
    run_defaults = fold_playbooks_alias(_config_layer(run_defaults, classes), None, notices)

    roots = config.get(SCENARIOS)
    if not isinstance(roots, list) or not roots:
        notices.append(_notice("error", None, SCENARIOS, "`scenarios` must be a non-empty list."))
        return {"files": files, "notices": notices}

    seen = set()

    def walk(node, parent):
        if not isinstance(node, dict) or not isinstance(node.get(NAME), str):
            notices.append(_notice("error", parent, None, "A scenario entry needs a string `name`."))
            return
        name = node[NAME]
        if name in seen:
            notices.append(_notice("error", name, NAME, "Scenario names must be unique across the run."))
            return
        seen.add(name)
        _check_keys(node, classes.node, name, notices)

        bare = fold_playbooks_alias(_config_layer(node, classes), name, notices)
        resolved = _ordered(drop_empty(deep_merge(run_defaults, bare)), classes)

        if PLATFORMS in resolved:
            selection = resolved[PLATFORMS]
            if any(isinstance(item, str) for item in selection or []):
                resolved.pop(PLATFORMS)
                notices.append(_notice(
                    "unresolved", name, PLATFORMS,
                    "Catalog selections have no projection yet. The instance name a selection gets "
                    "is an open question in the design, and the catalog's `vars` are opaque to Molecule. "
                    "Platforms are left out of this file."))
        elif parent is None and catalog:
            notices.append(_notice(
                "unresolved", name, PLATFORMS,
                "A root with no `platforms` selects the whole catalog, and catalog selections have no "
                "projection yet. Platforms are left out of this file."))

        paths = _playbook_paths(resolved)
        if paths:
            listed = ", ".join(f"{stage}: {path}" for stage, path in paths)
            notices.append(_notice(
                "unresolved", name, "provisioner.playbooks",
                "Playbook paths are copied as written. Today's Molecule resolves them against the "
                f"scenario directory `{SCENARIO_ROOT}/{name}/`. The spec does not say what a path "
                "in the root file is relative to, so whether they need rebasing is undecided. "
                f"Paths: {listed}."))

        if node.get(WAVE, 0) not in (0, None):
            notices.append(_notice(
                "lost", name, WAVE,
                f"`wave: {node[WAVE]}` orders this scenario among its siblings. Today's Molecule has "
                "no ordering tier, so it is dropped."))

        if parent is not None:
            notices.append(_notice(
                "lost", name, CHILDREN,
                f"Nested under `{parent}`, whose instances it shares in the tree. Today's Molecule has "
                "no parent edge, so this runs as an independent scenario without them."))

        files.append({"path": f"{SCENARIO_ROOT}/{name}/{SCENARIO_FILE}", "content": resolved})

        for child in node.get(CHILDREN) or []:
            walk(child, name)

    for root in roots:
        walk(root, None)

    return {"files": files, "notices": notices}
