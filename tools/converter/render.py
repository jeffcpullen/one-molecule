"""YAML in and out around the projection core. Shared by the CLI and the web page."""

import json

import yaml

from project import (
    COLLECTION_SCENARIOS_DIR, project, referenced_playbooks, run_workers, start_steps, workers_notices)


class _IndentedDumper(yaml.SafeDumper):
    """SafeDumper that indents sequences under their parent key."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def _represent_str(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_IndentedDumper.add_representer(str, _represent_str)


def dump(value):
    """Render a value as a block-style YAML document that starts with `---`.

    Args:
        value: the data to render.

    Returns:
        The YAML text.
    """
    body = yaml.dump(value, Dumper=_IndentedDumper, sort_keys=False,
                     default_flow_style=False, allow_unicode=True, width=10000)
    return "---\n" + body


def convert_text(text, schema, scenarios_dir=COLLECTION_SCENARIOS_DIR, workers=None, cpus=None, destroy="always"):
    """Parse a single-config molecule.yml and project it.

    Args:
        text: the YAML source.
        schema: the config schema as a dict.
        scenarios_dir: the scenarios directory the files are placed under.
        workers: the `--workers` value, which overrides the file's `workers`, or None.
        cpus: the CPU count a `cpus` or `cpus-1` value counts, or None for 1.
        destroy: the `--destroy` value, `always` or `never`.

    Returns:
        A dict with `files`, a list of {path, text}, `notices`, `playbooks`, the
        `referenced_playbooks` paths, and `order`, the `start_steps` result with the
        `requested` and `source` of its cap from `run_workers`.

    Raises:
        ValueError: when `workers` is not a value the schema accepts.
    """
    try:
        config = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        cap = run_workers(None, schema, workers, cpus)
        return {"files": [], "notices": [
            {"kind": "error", "node": None, "key": None, "message": f"YAML parse error: {exc}"}],
            "playbooks": [], "order": {**start_steps(None, cap["workers"]), **cap}}
    cap = run_workers(config, schema, workers, cpus)
    result = project(config, schema, scenarios_dir)
    files = [{"path": f["path"], "text": dump(f["content"])} for f in result["files"]]
    return {
        "files": files,
        "notices": result["notices"] + workers_notices(cap["workers"], scenarios_dir, destroy),
        "playbooks": referenced_playbooks(config),
        "order": {**start_steps(config, cap["workers"]), **cap},
    }


def convert_json(text, schema_text, scenarios_dir=COLLECTION_SCENARIOS_DIR, workers=None, cpus=None,
                 destroy="always"):
    """JSON wrapper of `convert_text` for the web page.

    Args:
        text: the YAML source.
        schema_text: the config schema as JSON text.
        scenarios_dir: the scenarios directory the files are placed under.
        workers: the `--workers` value, or None.
        cpus: the CPU count a `cpus` or `cpus-1` value counts, or None for 1.
        destroy: the `--destroy` value, `always` or `never`.

    Returns:
        The `convert_text` result as JSON text.
    """
    return json.dumps(convert_text(text, json.loads(schema_text), scenarios_dir, workers, cpus, destroy))
