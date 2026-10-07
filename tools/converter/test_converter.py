"""Fixture tests: each fixtures/<slug>/ holds the expected projection of examples/<slug>/after/molecule.yml."""

import pathlib
import re
import sys
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cli import ROOT, load_schema, load_starter, notices_json  # noqa: E402
from project import KeyClasses, deep_merge, drop_empty, project  # noqa: E402
from render import convert_text  # noqa: E402

FIXTURES = HERE / "fixtures"
SCHEMA = load_schema()


class ExampleFixtures(unittest.TestCase):
    """Every fixture directory matches the projection of its example, byte for byte."""

    def test_fixtures(self):
        slugs = sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())
        self.assertTrue(slugs)
        for slug in slugs:
            with self.subTest(slug=slug):
                source = ROOT / "examples" / slug / "after" / "molecule.yml"
                result = convert_text(source.read_text(), SCHEMA)
                expected_dir = FIXTURES / slug
                expected = {p.relative_to(expected_dir).as_posix(): p.read_text()
                            for p in expected_dir.rglob("*") if p.is_file()}
                produced = {f["path"]: f["text"] for f in result["files"]}
                produced["notices.json"] = notices_json(result["notices"])
                self.assertEqual(sorted(produced), sorted(expected))
                for path, text in produced.items():
                    self.assertEqual(text, expected[path], path)

    def test_rendering_is_lossless(self):
        for slug in sorted(p.name for p in FIXTURES.iterdir() if p.is_dir()):
            source = (ROOT / "examples" / slug / "after" / "molecule.yml").read_text()
            data = project(yaml.safe_load(source), SCHEMA)
            texts = {f["path"]: f["text"] for f in convert_text(source, SCHEMA)["files"]}
            for item in data["files"]:
                with self.subTest(slug=slug, path=item["path"]):
                    self.assertEqual(yaml.safe_load(texts[item["path"]]), item["content"])


class Starter(unittest.TestCase):
    """The starter file converts cleanly and names every key the spec declares."""

    def test_converts_to_one_scenario_without_errors(self):
        result = convert_text(load_starter(), SCHEMA)
        self.assertEqual([f["path"] for f in result["files"]], ["molecule/default/molecule.yml"])
        self.assertEqual([n for n in result["notices"] if n["kind"] == "error"], [])

    def test_live_scenario_is_a_minimal_config(self):
        result = convert_text(load_starter(), SCHEMA)
        self.assertEqual(yaml.safe_load(result["files"][0]["text"]),
                         {"driver": {"name": "default"}, "platforms": [{"name": "instance"}]})
        self.assertEqual(result["notices"], [])

    def test_names_every_declared_key(self):
        text = load_starter()
        definitions = SCHEMA["definitions"]
        keys = (set(SCHEMA["properties"]) | set(definitions["catalogPlatform"]["properties"])
                | set(definitions["config"]["properties"]) | set(definitions["node"]["properties"]))
        missing = sorted(k for k in keys if not re.search(rf"(^|\s){re.escape(k)}:", text, re.M))
        self.assertEqual(missing, [])

    def test_uncommenting_every_key_keeps_the_nesting(self):
        key_line = re.compile(r"^( *)# ((- )?[a-z_]+:.*)$")
        lines = [key_line.sub(r"\1\2", line) for line in load_starter().splitlines()]
        data = yaml.safe_load("\n".join(lines))
        self.assertEqual(list(data), ["platforms", "defaults", "scenarios"])
        node = data["scenarios"][0]
        self.assertEqual(set(node), set(SCHEMA["definitions"]["node"]["properties"]))
        self.assertEqual(set(data["defaults"]), set(SCHEMA["definitions"]["config"]["properties"]))


class Rules(unittest.TestCase):
    """The resolution rules from the 0.1.0 spec."""

    def test_key_classes_come_from_schema(self):
        classes = KeyClasses(SCHEMA)
        self.assertEqual(classes.node["name"], "node-intrinsic")
        self.assertEqual(classes.node["children"], "reserved-structural")
        self.assertTrue(classes.is_config("provisioner"))
        self.assertFalse(classes.is_config("wave"))

    def test_mappings_merge_lists_replace(self):
        merged = deep_merge({"a": {"x": 1, "y": [1, 2]}}, {"a": {"y": [3]}})
        self.assertEqual(merged, {"a": {"x": 1, "y": [3]}})

    def test_empty_value_clears(self):
        merged = drop_empty(deep_merge({"a": {"x": 1, "y": 2}}, {"a": {"x": None, "y": ""}}))
        self.assertEqual(merged, {"a": {}})

    def test_bare_does_not_cascade(self):
        config = {
            "defaults": {"verifier": {"name": "ansible"}},
            "scenarios": [{
                "name": "parent",
                "driver": {"name": "default"},
                "children": [{"name": "child"}],
            }],
        }
        files = {f["path"]: f["content"] for f in project(config, SCHEMA)["files"]}
        self.assertEqual(files["molecule/parent/molecule.yml"]["driver"], {"name": "default"})
        self.assertNotIn("driver", files["molecule/child/molecule.yml"])
        self.assertEqual(files["molecule/child/molecule.yml"]["verifier"], {"name": "ansible"})

    def test_tree_and_wave_reported_lost(self):
        config = {"scenarios": [{"name": "p", "children": [{"name": "c", "wave": 1}]}]}
        lost = {(n["node"], n["key"]) for n in project(config, SCHEMA)["notices"] if n["kind"] == "lost"}
        self.assertEqual(lost, {("c", "children"), ("c", "wave")})

    def test_catalog_selection_unresolved(self):
        config = {"platforms": [{"name": "vm"}], "scenarios": [{"name": "a"}, {"name": "b", "platforms": ["vm"]}]}
        result = project(config, SCHEMA)
        unresolved = {n["node"] for n in result["notices"] if n["key"] == "platforms"}
        self.assertEqual(unresolved, {"a", "b"})
        self.assertTrue(all("platforms" not in f["content"] for f in result["files"]))

    def test_playbook_paths_copied_as_written(self):
        config = {"scenarios": [{"name": "a", "playbooks": {"verify": "../../tests/verify.yml"}}]}
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [])
        playbooks = result["files"][0]["content"]["provisioner"]["playbooks"]
        self.assertEqual(playbooks, {"verify": "../../tests/verify.yml"})

    def test_unknown_key_is_error(self):
        result = project({"scenarios": [{"name": "a", "parent": "x"}]}, SCHEMA)
        self.assertIn(("error", "parent"), {(n["kind"], n["key"]) for n in result["notices"]})

    def test_non_config_key_in_defaults_is_error(self):
        result = project({"defaults": {"wave": 1}, "scenarios": [{"name": "a"}]}, SCHEMA)
        self.assertIn(("error", "defaults", "wave"),
                      {(n["kind"], n["node"], n["key"]) for n in result["notices"]})
        self.assertEqual(result["files"][0]["content"], {})


if __name__ == "__main__":
    unittest.main()
