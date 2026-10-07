"""Project a single-config molecule.yml into today's per-scenario file tree.

Standard library only. Key classes come from the schema's `x-class` annotations.
"""

import json
import posixpath

PLAYBOOKS_ALIAS = "playbooks"
PROVISIONER = "provisioner"
PLATFORMS = "platforms"
CHILDREN = "children"
WAVE = "wave"
NAME = "name"
DEFAULTS = "defaults"
SCENARIOS = "scenarios"
COLLECTION_SCENARIOS_DIR = "extensions/molecule"
PROJECT_SCENARIOS_DIR = "molecule"
SCENARIOS_DIRS = (COLLECTION_SCENARIOS_DIR, PROJECT_SCENARIOS_DIR)
SCENARIO_FILE = "molecule.yml"
BASE_CONFIG_PATHS = {
    COLLECTION_SCENARIOS_DIR: f"{COLLECTION_SCENARIOS_DIR}/config.yml",
    PROJECT_SCENARIOS_DIR: ".config/molecule/config.yml",
}
SHARED_ROOT = "default"
SHARED_STATE = "shared_state"
INSTANCE_STAGES = ("create", "destroy")


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


def select_platforms(selection, catalog, node_name, notices):
    """Turn a platform selection into molecule platform entries.

    A catalog name becomes a copy of that catalog entry named `<node>-<catalog name>`.
    An inline platform object is copied as written.

    Args:
        selection: the node's resolved `platforms` list.
        catalog: {catalog name: catalog entry}.
        node_name: the scenario that selects them.
        notices: list that receives an error notice for an unknown catalog name.

    Returns:
        The list of platform entries.
    """
    out = []
    for item in selection:
        if not isinstance(item, str):
            out.append(_copy(item))
            continue
        entry = catalog.get(item)
        if entry is None:
            notices.append(_notice(
                "error", node_name, PLATFORMS, f"`{item}` is not a name in the platform catalog."))
            continue
        entry = _copy(entry)
        entry[NAME] = f"{node_name}-{item}"
        out.append(entry)
    return out


def _read_catalog(entries, notices):
    catalog = {}
    if not isinstance(entries, list):
        notices.append(_notice("error", None, PLATFORMS, "The platform catalog is not a list."))
        return catalog
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get(NAME), str) or not entry[NAME]:
            notices.append(_notice("error", None, PLATFORMS, "A catalog entry needs a string `name`."))
            continue
        if entry[NAME] in catalog:
            notices.append(_notice(
                "error", None, PLATFORMS, f"Catalog name `{entry[NAME]}` is defined twice."))
            continue
        catalog[entry[NAME]] = entry
    return catalog


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


def _check_keys(mapping, allowed, where, notices):
    for key in mapping:
        if key not in allowed:
            notices.append(_notice("error", where, key, f"`{key}` is not a key the spec declares here."))


def _bare_stages(node):
    stages = set()
    alias = node.get(PLAYBOOKS_ALIAS)
    if isinstance(alias, dict):
        stages.update(alias)
    provisioner = node.get(PROVISIONER)
    if isinstance(provisioner, dict) and isinstance(provisioner.get("playbooks"), dict):
        stages.update(provisioner["playbooks"])
    return stages


def _selects_any(selection, catalog):
    if not isinstance(selection, list):
        return False
    return any(isinstance(item, dict) or item in catalog for item in selection)


def shared_state_blocker(roots, run_defaults, classes, catalog):
    """Return why a tree cannot map onto Molecule's `shared_state`, or None when it can.

    The tree maps when it has exactly one root, named `default`, with at least one child,
    every other node is a direct child of it, the root resolves at least one platform,
    the root's resolved `scenario.test_sequence`, when set, has both `create` and
    `destroy`, and no child selects platforms or sets its own `create` or `destroy`
    playbook. A mapped child is projected with the parent's resolved platform entries.

    Args:
        roots: the `scenarios` list.
        run_defaults: the run `defaults:` layer, with the playbooks alias folded.
        classes: the `KeyClasses` read from the schema.
        catalog: {catalog name: catalog entry}.

    Returns:
        A sentence fragment naming the first condition that fails, or None.
    """
    if len(roots) != 1:
        return "the run has more than one root"
    root = roots[0]
    if not isinstance(root, dict):
        return "the root is not a mapping"
    if root.get(NAME) != SHARED_ROOT:
        return f"the root is named `{root.get(NAME)}`, not `{SHARED_ROOT}`"
    merged = deep_merge(run_defaults, _config_layer(root, classes))
    selection = merged[PLATFORMS] if PLATFORMS in merged else list(catalog)
    if not _selects_any(selection, catalog):
        return f"`{SHARED_ROOT}` resolves no platforms for its children to share"
    scenario = merged.get("scenario")
    sequence = scenario.get("test_sequence") if isinstance(scenario, dict) else None
    if isinstance(sequence, list):
        missing = [stage for stage in INSTANCE_STAGES if stage not in sequence]
        if missing:
            return (f"the `{SHARED_ROOT}` test_sequence has no `{missing[0]}`, and `{SHARED_STATE}` "
                    f"runs `{missing[0]}` only from that sequence")
    for child in root.get(CHILDREN) or []:
        if not isinstance(child, dict):
            return "a child is not a mapping"
        name = child.get(NAME)
        if child.get(CHILDREN):
            return f"`{name}` has children of its own, and `{SHARED_STATE}` shares one level only"
        if PLATFORMS in child:
            return f"`{name}` selects platforms of its own"
        own = sorted(set(INSTANCE_STAGES) & _bare_stages(child))
        if own:
            return f"`{name}` sets its own `{own[0]}` playbook"
    return None


def project(config, schema, scenarios_dir=COLLECTION_SCENARIOS_DIR):
    """Project a single-config molecule.yml into per-scenario files.

    Args:
        config: the parsed single-config molecule.yml.
        schema: the config schema as a dict (generated JSON form).
        scenarios_dir: the scenarios directory, `extensions/molecule` for a collection
            or `molecule` for a standalone role or playbook project.

    Returns:
        A dict with `files`, a list of {path, content} with any base `config.yml` first
        (`extensions/molecule/config.yml` for a collection, `.config/molecule/config.yml`
        at the project root otherwise) and the scenario files in tree pre-order, and
        `notices`, a list of
        {kind, node, key, message} where kind is `error`, `unresolved` or `lost`.
    """
    classes = KeyClasses(schema)
    notices = []
    files = []

    if scenarios_dir not in SCENARIOS_DIRS:
        notices.append(_notice(
            "error", None, None,
            f"`{scenarios_dir}` is not a scenarios directory. Use one of: " + ", ".join(SCENARIOS_DIRS) + "."))
        return {"files": files, "notices": notices}

    if not isinstance(config, dict):
        notices.append(_notice("error", None, None, "The file is not a mapping."))
        return {"files": files, "notices": notices}
    _check_keys(config, classes.run, None, notices)

    catalog = _read_catalog(config.get(PLATFORMS) or [], notices)
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

    has_children = any(isinstance(r, dict) and r.get(CHILDREN) for r in roots)
    blocker = shared_state_blocker(roots, run_defaults, classes, catalog) if has_children else None
    shared = has_children and blocker is None
    if shared:
        files.append({"path": BASE_CONFIG_PATHS[scenarios_dir], "content": {SHARED_STATE: True}})

    seen = set()

    def walk(node, parent, parent_platforms):
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
        merged = deep_merge(run_defaults, bare)
        if PLATFORMS not in merged and parent is None and catalog:
            merged[PLATFORMS] = list(catalog)
        if isinstance(merged.get(PLATFORMS), list):
            for item in merged[PLATFORMS]:
                if isinstance(item, dict) and item.get(NAME) in catalog:
                    notices.append(_notice(
                        "error", name, PLATFORMS,
                        f"Inline platform `{item[NAME]}` has the same name as a catalog entry."))
            merged[PLATFORMS] = select_platforms(merged[PLATFORMS], catalog, name, notices)
        if shared and parent is not None and parent_platforms is not None:
            merged[PLATFORMS] = _copy(parent_platforms)
        resolved = _ordered(merged, classes)

        wave, wave_ok = node_wave(node)
        if not wave_ok:
            notices.append(_notice(
                "error", name, WAVE, f"`wave: {json.dumps(node[WAVE], default=str)}` is not an integer."))
        elif wave != 0:
            notices.append(_notice(
                "lost", name, WAVE,
                f"`wave: {wave}` orders this scenario among its siblings. Today's Molecule has "
                "no ordering tier, so it is dropped."))

        if parent is not None and not shared:
            notices.append(_notice(
                "lost", name, CHILDREN,
                f"Nested under `{parent}`, whose instances it shares in the tree. Today's Molecule has "
                f"no parent edge, and this tree cannot map onto `{SHARED_STATE}` because {blocker}, "
                "so this runs as an independent scenario without them."))

        files.append({"path": f"{scenarios_dir}/{name}/{SCENARIO_FILE}", "content": resolved})

        for child in node.get(CHILDREN) or []:
            walk(child, name, resolved.get(PLATFORMS))

    for root in roots:
        walk(root, None, None)

    return {"files": files, "notices": notices}


def node_wave(node):
    """Read a node's `wave`.

    Args:
        node: the node mapping as written.

    Returns:
        (wave, valid). An absent `wave` is (0, True). An integer, or a float with an
        integral value, is that integer and valid. Anything else, including a bool and
        null, is (0, False).
    """
    if WAVE not in node:
        return 0, True
    value = node[WAVE]
    if isinstance(value, bool):
        return 0, False
    if isinstance(value, int):
        return value, True
    if isinstance(value, float) and value.is_integer():
        return int(value), True
    return 0, False


def scenario_nodes(config):
    """List the run's scenario nodes in tree pre-order.

    Entries without a string `name`, and repeats of a name already seen, are skipped
    with their subtrees, as `project` skips them.

    Args:
        config: the parsed single-config molecule.yml.

    Returns:
        A list of {name, parent, wave, node, children} where `parent` and each entry of
        `children` are indexes into the list, `parent` is None for a root, `wave` is the
        `node_wave` value, which is 0 for an invalid wave, and `node` is the node mapping
        as written.
    """
    nodes = []
    if not isinstance(config, dict) or not isinstance(config.get(SCENARIOS), list):
        return nodes
    seen = set()

    def walk(node, parent):
        if not isinstance(node, dict) or not isinstance(node.get(NAME), str) or node[NAME] in seen:
            return
        seen.add(node[NAME])
        wave = node_wave(node)[0]
        index = len(nodes)
        nodes.append({"name": node[NAME], "parent": parent, "wave": wave, "node": node, "children": []})
        if parent is not None:
            nodes[parent]["children"].append(index)
        children = node.get(CHILDREN)
        for child in children if isinstance(children, list) else []:
            walk(child, index)

    for root in config[SCENARIOS]:
        walk(root, None)
    return nodes


def _playbook_layer(layer):
    if not isinstance(layer, dict):
        return {}
    picked = {}
    if isinstance(layer.get(PLAYBOOKS_ALIAS), dict):
        picked[PLAYBOOKS_ALIAS] = layer[PLAYBOOKS_ALIAS]
    provisioner = layer.get(PROVISIONER)
    if isinstance(provisioner, dict) and isinstance(provisioner.get("playbooks"), dict):
        picked[PROVISIONER] = {"playbooks": provisioner["playbooks"]}
    return fold_playbooks_alias(picked, None, [])


def _strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    return []


def resolve_path(value, scenarios_dir, name):
    """Resolve a playbook path from a scenario's directory to a project-relative path.

    Args:
        value: the path as written.
        scenarios_dir: the scenarios directory.
        name: the scenario name.

    Returns:
        The normalised POSIX path. An absolute path stays absolute, and a path that
        climbs above the project root keeps its leading `..`.
    """
    return posixpath.normpath(posixpath.join(scenarios_dir, name, value))


def referenced_playbooks(config, scenarios_dir=COLLECTION_SCENARIOS_DIR):
    """List every playbook the file references, as project-relative paths.

    Each node's playbooks are its `playbooks` and `provisioner.playbooks` merged over
    those under `defaults:`, as `project` merges them, so a stage the node sets itself
    hides the defaults path for that stage. Each value is resolved from the node's
    scenario directory.

    Args:
        config: the parsed single-config molecule.yml.
        scenarios_dir: the scenarios directory.

    Returns:
        The sorted, deduplicated list of paths.
    """
    nodes = scenario_nodes(config)
    defaults = _playbook_layer(config.get(DEFAULTS) if isinstance(config, dict) else None)
    paths = set()
    for entry in nodes:
        merged = deep_merge(defaults, _playbook_layer(entry["node"]))
        for value in _strings(merged.get(PROVISIONER, {}).get("playbooks")):
            paths.add(resolve_path(value, scenarios_dir, entry["name"]))
    return sorted(paths)


def start_steps(config, workers=None):
    """Return the step at which each scenario starts.

    Each scenario takes one step. A child is ready once its parent has completed. Among
    nodes that share a parent, roots sharing the run, the lowest wave is ready first, and
    a node is ready only once every sibling in a lower wave has completed its whole
    subtree. With a cap, at most `workers` scenarios start per step. Ready scenarios beyond the cap
    wait, the earliest ready first, ties in pre-order. A wave that `project` reports as
    an error is ordered as wave 0.

    Args:
        config: the parsed single-config molecule.yml.
        workers: the cap, an integer of at least 1, or None for no cap.

    Returns:
        A dict with `workers`, the cap as given or None, and `scenarios`, a pre-order list of
        {name, parent, step} where `parent` is a name or None and `step` counts from 1.

    Raises:
        ValueError: when `workers` is below 1.
    """
    nodes = scenario_nodes(config)
    if workers is not None and (not isinstance(workers, int) or isinstance(workers, bool) or workers < 1):
        raise ValueError("workers must be an integer of at least 1")
    cap = len(nodes) if workers is None else workers
    roots = [i for i, n in enumerate(nodes) if n["parent"] is None]
    started = {}
    ready_since = {}

    def siblings(index):
        parent = nodes[index]["parent"]
        return roots if parent is None else nodes[parent]["children"]

    def subtree_done(index, step):
        if started.get(index, step) >= step:
            return False
        return all(subtree_done(c, step) for c in nodes[index]["children"])

    def ready(index, step):
        parent = nodes[index]["parent"]
        if parent is not None and started.get(parent, step) >= step:
            return False
        wave = nodes[index]["wave"]
        return all(subtree_done(j, step) for j in siblings(index) if nodes[j]["wave"] < wave)

    step = 0
    while len(started) < len(nodes):
        step += 1
        for index in range(len(nodes)):
            if index not in started and index not in ready_since and ready(index, step):
                ready_since[index] = step
        queue = sorted((i for i in ready_since if i not in started), key=lambda i: (ready_since[i], i))
        if not queue:
            break
        for index in queue[:cap]:
            started[index] = step
    return {
        "workers": workers,
        "scenarios": [
            {
                "name": n["name"],
                "parent": None if n["parent"] is None else nodes[n["parent"]]["name"],
                "step": started.get(i),
            }
            for i, n in enumerate(nodes)
        ],
    }
