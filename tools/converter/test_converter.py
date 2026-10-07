"""Fixture tests: each fixtures/<slug>/ holds the expected projection of the example's single-file molecule.yml."""

import contextlib
import io
import pathlib
import re
import sys
import tempfile
import unittest

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cli import (  # noqa: E402
    example_playbooks, example_scenarios_dir, example_source, load_schema, load_starter, notices_json, order_text,
    playbooks_in)
from cli import main as cli_main  # noqa: E402
from project import (  # noqa: E402
    CPU_OFFSETS, KeyClasses, deep_merge, project, referenced_playbooks, run_workers, start_steps, workers_words)
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
                source = example_source(slug)
                result = convert_text(source.read_text(), SCHEMA, example_scenarios_dir(slug))
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
            source = example_source(slug).read_text()
            scenarios_dir = example_scenarios_dir(slug)
            data = project(yaml.safe_load(source), SCHEMA, scenarios_dir)
            texts = {f["path"]: f["text"] for f in convert_text(source, SCHEMA, scenarios_dir)["files"]}
            for item in data["files"]:
                with self.subTest(slug=slug, path=item["path"]):
                    self.assertEqual(yaml.safe_load(texts[item["path"]]), item["content"])


class Starter(unittest.TestCase):
    """The starter file converts cleanly and names every key the spec declares."""

    def test_converts_to_one_scenario_without_errors(self):
        result = convert_text(load_starter(), SCHEMA)
        self.assertEqual([f["path"] for f in result["files"]], ["extensions/molecule/integration_sample_filter/molecule.yml"])
        self.assertEqual([n for n in result["notices"] if n["kind"] == "error"], [])

    def test_live_scenario_names_the_creator_scaffold_playbooks(self):
        result = convert_text(load_starter(), SCHEMA)
        self.assertEqual(yaml.safe_load(result["files"][0]["text"]), {
            "platforms": [{"name": "na"}],
            "provisioner": {
                "name": "ansible",
                "playbooks": {
                    "cleanup": "${MOLECULE_PROJECT_DIRECTORY}/extensions/molecule/utils/playbooks/noop.yml",
                    "converge": "${MOLECULE_PROJECT_DIRECTORY}/extensions/molecule/utils/playbooks/converge.yml",
                    "destroy": "${MOLECULE_PROJECT_DIRECTORY}/extensions/molecule/utils/playbooks/noop.yml",
                    "prepare": "${MOLECULE_PROJECT_DIRECTORY}/extensions/molecule/utils/playbooks/noop.yml",
                },
                "config_options": {"defaults": {"collections_path": "${ANSIBLE_COLLECTIONS_PATH}"}},
            },
            "scenario": {
                "test_sequence": ["prepare", "converge"],
                "destroy_sequence": ["destroy"],
            },
        })
        self.assertEqual(result["notices"], [])

    def test_lines_stay_short(self):
        long_lines = [line for line in load_starter().splitlines() if len(line) > 100]
        self.assertEqual(long_lines, [])

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
        self.assertEqual(list(data), ["workers", "platforms", "defaults", "scenarios"])
        self.assertEqual(data["workers"], 1)
        node = data["scenarios"][0]
        self.assertEqual(set(node), set(SCHEMA["definitions"]["node"]["properties"]))
        self.assertEqual(set(data["defaults"]), set(SCHEMA["definitions"]["config"]["properties"]))


class Rules(unittest.TestCase):
    """The resolution rules from the latest released spec."""

    def test_key_classes_come_from_schema(self):
        classes = KeyClasses(SCHEMA)
        self.assertEqual(classes.node["name"], "node-intrinsic")
        self.assertEqual(classes.node["children"], "reserved-structural")
        self.assertTrue(classes.is_config("provisioner"))
        self.assertFalse(classes.is_config("wave"))

    def test_mappings_merge_lists_replace(self):
        merged = deep_merge({"a": {"x": 1, "y": [1, 2]}}, {"a": {"y": [3]}})
        self.assertEqual(merged, {"a": {"x": 1, "y": [3]}})

    def test_list_replaces_the_defaults_list(self):
        config = {
            "defaults": {"scenario": {"test_sequence": ["prepare", "converge", "verify"]}},
            "scenarios": [{"name": "a", "scenario": {"test_sequence": ["converge"]}}],
        }
        content = project(config, SCHEMA)["files"][0]["content"]
        self.assertEqual(content["scenario"]["test_sequence"], ["converge"])

    def test_empty_values_project_as_written(self):
        config = {
            "defaults": {"provisioner": {"inventory": {"group_vars": {"all": {"x": 1, "y": 2}}}}},
            "scenarios": [{"name": "a", "provisioner": {"inventory": {"group_vars": {"all": {"x": None, "y": ""}}}}}],
        }
        content = project(config, SCHEMA)["files"][0]["content"]
        self.assertEqual(content["provisioner"]["inventory"]["group_vars"]["all"], {"x": None, "y": ""})

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
        self.assertEqual(files["extensions/molecule/parent/molecule.yml"]["driver"], {"name": "default"})
        self.assertNotIn("driver", files["extensions/molecule/child/molecule.yml"])
        self.assertEqual(files["extensions/molecule/child/molecule.yml"]["verifier"], {"name": "ansible"})

    def test_tree_and_wave_reported_lost(self):
        config = {"scenarios": [{"name": "p", "children": [{"name": "c", "wave": 1}]}]}
        lost = {(n["node"], n["key"]) for n in project(config, SCHEMA)["notices"] if n["kind"] == "lost"}
        self.assertEqual(lost, {("c", "children"), ("c", "wave")})

    def test_catalog_selection_is_named_for_the_scenario(self):
        config = {
            "platforms": [{"name": "vm", "image": "debian:13"}, {"name": "ct"}],
            "scenarios": [
                {"name": "a", "children": [{"name": "c"}]},
                {"name": "b", "platforms": ["vm", {"name": "local"}]},
            ],
        }
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [
            {"kind": "lost", "node": "c", "key": "children", "message": result["notices"][0]["message"]},
        ])
        files = {f["path"]: f["content"] for f in result["files"]}
        self.assertEqual(files["extensions/molecule/a/molecule.yml"]["platforms"], [
            {"name": "a-vm", "image": "debian:13"},
            {"name": "a-ct"},
        ])
        self.assertNotIn("platforms", files["extensions/molecule/c/molecule.yml"])
        self.assertEqual(files["extensions/molecule/b/molecule.yml"]["platforms"], [
            {"name": "b-vm", "image": "debian:13"},
            {"name": "local"},
        ])
        self.assertEqual(config["platforms"][0]["name"], "vm")

    def test_default_root_with_children_maps_onto_shared_state(self):
        config = {
            "platforms": [{"name": "instance"}],
            "defaults": {"playbooks": {"create": "c.yml", "destroy": "d.yml"}},
            "scenarios": [{"name": "default", "children": [{"name": "a"}, {"name": "b"}]}],
        }
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [])
        self.assertEqual(result["files"][0], {"path": "extensions/molecule/config.yml", "content": {"shared_state": True}})
        self.assertEqual([f["path"] for f in result["files"][1:]], [
            "extensions/molecule/default/molecule.yml",
            "extensions/molecule/a/molecule.yml",
            "extensions/molecule/b/molecule.yml",
        ])

    def test_shared_state_children_carry_the_parent_instances(self):
        config = {
            "platforms": [{"name": "instance", "image": "fedora:42"}],
            "scenarios": [{"name": "default", "children": [{"name": "a"}, {"name": "b"}]}],
        }
        files = {f["path"]: f["content"] for f in project(config, SCHEMA)["files"]}
        expected = [{"name": "default-instance", "image": "fedora:42"}]
        self.assertEqual(files["extensions/molecule/default/molecule.yml"]["platforms"], expected)
        self.assertEqual(files["extensions/molecule/a/molecule.yml"]["platforms"], expected)
        self.assertEqual(files["extensions/molecule/b/molecule.yml"]["platforms"], expected)

    def test_lost_children_select_no_platforms(self):
        config = {
            "platforms": [{"name": "instance"}],
            "scenarios": [{"name": "p", "children": [{"name": "c"}]}],
        }
        files = {f["path"]: f["content"] for f in project(config, SCHEMA)["files"]}
        self.assertNotIn("platforms", files["extensions/molecule/c/molecule.yml"])

    def test_shared_state_config_follows_the_scenarios_dir(self):
        config = {
            "platforms": [{"name": "instance"}],
            "scenarios": [{"name": "default", "children": [{"name": "a"}]}],
        }
        paths = [f["path"] for f in project(config, SCHEMA, "molecule")["files"]]
        self.assertEqual(paths, [".config/molecule/config.yml", "molecule/default/molecule.yml", "molecule/a/molecule.yml"])
        paths = [f["path"] for f in project(config, SCHEMA)["files"]]
        self.assertEqual(paths[0], "extensions/molecule/config.yml")

    def test_defaults_platforms_do_not_block_shared_state(self):
        config = {
            "platforms": [{"name": "vm"}, {"name": "ct"}],
            "defaults": {"platforms": ["vm"]},
            "scenarios": [{"name": "default", "children": [{"name": "a"}]}],
        }
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [])
        files = {f["path"]: f["content"] for f in result["files"]}
        self.assertEqual(files["extensions/molecule/config.yml"], {"shared_state": True})
        self.assertEqual(files["extensions/molecule/a/molecule.yml"]["platforms"], [{"name": "default-vm"}])

    def test_parent_catalog_subset_reaches_the_children(self):
        config = {
            "platforms": [{"name": "vm", "image": "debian:13"}, {"name": "ct", "image": "fedora:42"}],
            "scenarios": [{"name": "default", "platforms": ["ct"], "children": [{"name": "a"}]}],
        }
        files = {f["path"]: f["content"] for f in project(config, SCHEMA)["files"]}
        expected = [{"name": "default-ct", "image": "fedora:42"}]
        self.assertEqual(files["extensions/molecule/default/molecule.yml"]["platforms"], expected)
        self.assertEqual(files["extensions/molecule/a/molecule.yml"]["platforms"], expected)

    def test_inline_parent_platform_reaches_the_children_verbatim(self):
        inline = {"name": "box", "image": "fedora:42"}
        config = {"scenarios": [{"name": "default", "platforms": [inline], "children": [{"name": "a"}]}]}
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [])
        files = {f["path"]: f["content"] for f in result["files"]}
        self.assertEqual(files["extensions/molecule/default/molecule.yml"]["platforms"], [inline])
        self.assertEqual(files["extensions/molecule/a/molecule.yml"]["platforms"], [inline])

    def test_tree_without_children_writes_no_base_config(self):
        paths = [f["path"] for f in project({"scenarios": [{"name": "default"}]}, SCHEMA)["files"]]
        self.assertEqual(paths, ["extensions/molecule/default/molecule.yml"])

    def test_trees_that_cannot_map_onto_shared_state_stay_lost(self):
        catalog = [{"name": "vm"}]
        cases = {
            "the root is named `p`, not `default`": {"scenarios": [{"name": "p", "children": [{"name": "c"}]}]},
            "the run has more than one root": {
                "scenarios": [{"name": "default", "children": [{"name": "c"}]}, {"name": "other"}]},
            "`default` resolves no platforms for its children to share": {
                "scenarios": [{"name": "default", "children": [{"name": "c"}]}]},
            "the `default` test_sequence has no `create`, and `shared_state` runs `create` only from that sequence": {
                "scenarios": [{"name": "default", "scenario": {"test_sequence": ["verify", "destroy"]},
                               "children": [{"name": "c"}]}]},
            "the `default` test_sequence has no `destroy`, and `shared_state` runs `destroy` only from that sequence": {
                "defaults": {"scenario": {"test_sequence": ["create", "converge"]}},
                "scenarios": [{"name": "default", "children": [{"name": "c"}]}]},
            "`c` has children of its own, and `shared_state` shares one level only": {
                "scenarios": [{"name": "default", "children": [{"name": "c", "children": [{"name": "g"}]}]}]},
            "`c` selects platforms of its own": {
                "scenarios": [{"name": "default", "children": [{"name": "c", "platforms": ["vm"]}]}]},
            "`c` sets its own `create` playbook": {
                "scenarios": [{"name": "default", "children": [{"name": "c", "playbooks": {"create": "x.yml"}}]}]},
            "`c` sets its own `destroy` playbook": {
                "scenarios": [{"name": "default", "children": [
                    {"name": "c", "provisioner": {"playbooks": {"destroy": "x.yml"}}}]}]},
        }
        for reason, config in cases.items():
            with self.subTest(reason=reason):
                if reason != "`default` resolves no platforms for its children to share":
                    config = {"platforms": catalog, **config}
                result = project(config, SCHEMA)
                self.assertNotIn("config.yml", [f["path"].rsplit("/", 1)[-1] for f in result["files"]])
                lost = [n for n in result["notices"] if n["kind"] == "lost" and n["key"] == "children"]
                self.assertTrue(lost)
                for notice in lost:
                    self.assertIn(f"cannot map onto `shared_state` because {reason},", notice["message"])

    def test_unknown_scenarios_dir_is_error(self):
        result = project({"scenarios": [{"name": "a"}]}, SCHEMA, "tests/molecule")
        self.assertEqual(result["files"], [])
        self.assertEqual([n["kind"] for n in result["notices"]], ["error"])

    def test_unknown_catalog_name_is_error(self):
        result = project({"platforms": [{"name": "vm"}], "scenarios": [{"name": "a", "platforms": ["nope"]}]}, SCHEMA)
        self.assertIn(("error", "a", "platforms"), {(n["kind"], n["node"], n["key"]) for n in result["notices"]})
        self.assertEqual(result["files"][0]["content"]["platforms"], [])

    def test_inline_name_matching_catalog_is_error(self):
        result = project({"platforms": [{"name": "vm"}], "scenarios": [{"name": "a", "platforms": [{"name": "vm"}]}]},
                         SCHEMA)
        self.assertIn(("error", "a", "platforms"), {(n["kind"], n["node"], n["key"]) for n in result["notices"]})

    def test_relative_playbook_paths_start_from_the_project_root(self):
        config = {
            "defaults": {"provisioner": {"playbooks": {"converge": "playbooks/molecule/converge.yml"}}},
            "scenarios": [{"name": "a", "playbooks": {"verify": "tests/verify.yml", "prepare": "../up.yml"}},
                          {"name": "b"}],
        }
        result = project(config, SCHEMA, "molecule")
        self.assertEqual(result["notices"], [])
        files = {f["path"]: f["content"]["provisioner"]["playbooks"] for f in result["files"]}
        self.assertEqual(files["molecule/a/molecule.yml"], {
            "converge": "${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/converge.yml",
            "verify": "${MOLECULE_PROJECT_DIRECTORY}/tests/verify.yml",
            "prepare": "${MOLECULE_PROJECT_DIRECTORY}/../up.yml",
        })
        self.assertEqual(files["molecule/b/molecule.yml"],
                         {"converge": "${MOLECULE_PROJECT_DIRECTORY}/playbooks/molecule/converge.yml"})
        self.assertEqual(config["defaults"]["provisioner"]["playbooks"]["converge"], "playbooks/molecule/converge.yml")

    def test_absolute_and_variable_paths_copied_as_written(self):
        written = {
            "create": "/opt/playbooks/create.yml",
            "verify": "${MOLECULE_PROJECT_DIRECTORY}/tests/verify.yml",
            "prepare": "$MOLECULE_PROJECT_DIRECTORY/tests/prepare.yml",
            "converge": "${MOLECULE_SCENARIO_DIRECTORY}/converge.yml",
        }
        result = project({"scenarios": [{"name": "a", "playbooks": written}]}, SCHEMA)
        self.assertEqual(result["notices"], [])
        self.assertEqual(result["files"][0]["content"]["provisioner"]["playbooks"], written)

    def test_unknown_key_is_error(self):
        result = project({"scenarios": [{"name": "a", "parent": "x"}]}, SCHEMA)
        self.assertIn(("error", "parent"), {(n["kind"], n["key"]) for n in result["notices"]})

    def test_non_config_key_in_defaults_is_error(self):
        result = project({"defaults": {"wave": 1}, "scenarios": [{"name": "a"}]}, SCHEMA)
        self.assertIn(("error", "defaults", "wave"),
                      {(n["kind"], n["node"], n["key"]) for n in result["notices"]})
        self.assertEqual(result["files"][0]["content"], {})


class CatalogHostVars(unittest.TestCase):
    """A catalog entry's host_vars reach each selecting scenario under its instance name (tree-spec catalog-host-vars-*)."""

    def test_schema_declares_host_vars_on_a_catalog_entry(self):
        self.assertIn("host_vars", SCHEMA["definitions"]["catalogPlatform"]["properties"])

    def test_translated_for_every_selection_and_never_a_platform_key(self):
        config = {
            "platforms": [{"name": "vm", "image": "debian:13", "host_vars": {"port": 22}}, {"name": "ct"}],
            "scenarios": [{"name": "a"}, {"name": "b", "platforms": ["vm"]}, {"name": "c", "platforms": ["ct"]}],
        }
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [])
        files = {f["path"]: f["content"] for f in result["files"]}
        a = files["extensions/molecule/a/molecule.yml"]
        self.assertEqual(a["platforms"], [{"name": "a-vm", "image": "debian:13"}, {"name": "a-ct"}])
        self.assertEqual(a["provisioner"], {"inventory": {"host_vars": {"a-vm": {"port": 22}}}})
        b = files["extensions/molecule/b/molecule.yml"]
        self.assertEqual(b["platforms"], [{"name": "b-vm", "image": "debian:13"}])
        self.assertEqual(b["provisioner"]["inventory"]["host_vars"], {"b-vm": {"port": 22}})
        self.assertNotIn("provisioner", files["extensions/molecule/c/molecule.yml"])
        for content in files.values():
            for platform in content.get("platforms", []):
                self.assertNotIn("host_vars", platform)
        self.assertEqual(config["platforms"][0]["host_vars"], {"port": 22})

    def test_scenario_host_vars_merge_over_the_catalog_and_win(self):
        config = {
            "platforms": [{"name": "vm", "host_vars": {"port": 22, "user": "root", "opts": {"x": 1, "y": 2}}}],
            "defaults": {"provisioner": {"name": "ansible", "inventory": {
                "group_vars": {"all": {"g": 1}},
                "host_vars": {"a-vm": {"opts": {"y": 3}}},
            }}},
            "scenarios": [{"name": "a", "provisioner": {"inventory": {"host_vars": {
                "a-vm": {"user": "admin"},
                "other": {"k": "v"},
            }}}}],
        }
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [])
        provisioner = result["files"][0]["content"]["provisioner"]
        self.assertEqual(provisioner, {
            "name": "ansible",
            "inventory": {
                "group_vars": {"all": {"g": 1}},
                "host_vars": {
                    "a-vm": {"port": 22, "user": "admin", "opts": {"x": 1, "y": 3}},
                    "other": {"k": "v"},
                },
            },
        })

    def test_scenario_null_for_a_variable_wins(self):
        config = {
            "platforms": [{"name": "vm", "host_vars": {"port": 22}}],
            "scenarios": [{"name": "a", "provisioner": {"inventory": {"host_vars": {"a-vm": {"port": None}}}}}],
        }
        provisioner = project(config, SCHEMA)["files"][0]["content"]["provisioner"]
        self.assertEqual(provisioner["inventory"]["host_vars"], {"a-vm": {"port": None}})

    def test_inline_platform_is_untouched(self):
        inline = {"name": "box", "host_vars": {"k": 1}}
        result = project({"scenarios": [{"name": "a", "platforms": [inline]}]}, SCHEMA)
        self.assertEqual(result["files"][0]["content"], {"platforms": [inline]})

    def test_shared_state_children_carry_the_parent_instance_host_vars(self):
        config = {
            "platforms": [{"name": "instance", "host_vars": {"port": 22}}],
            "scenarios": [{"name": "default", "children": [
                {"name": "a"},
                {"name": "b", "provisioner": {"inventory": {"host_vars": {"default-instance": {"port": 2222}}}}},
            ]}],
        }
        result = project(config, SCHEMA)
        self.assertEqual(result["notices"], [])
        files = {f["path"]: f["content"] for f in result["files"]}
        for name, port in (("default", 22), ("a", 22), ("b", 2222)):
            with self.subTest(name=name):
                content = files[f"extensions/molecule/{name}/molecule.yml"]
                self.assertEqual(content["platforms"], [{"name": "default-instance"}])
                self.assertEqual(content["provisioner"]["inventory"]["host_vars"], {"default-instance": {"port": port}})

    def test_lost_children_get_none(self):
        config = {
            "platforms": [{"name": "vm", "host_vars": {"port": 22}}],
            "scenarios": [{"name": "p", "children": [{"name": "c"}]}],
        }
        files = {f["path"]: f["content"] for f in project(config, SCHEMA)["files"]}
        self.assertNotIn("provisioner", files["extensions/molecule/c/molecule.yml"])

    def test_bad_values_are_errors(self):
        result = project({"platforms": [{"name": "vm", "host_vars": ["x"]}], "scenarios": [{"name": "a"}]}, SCHEMA)
        self.assertIn(("error", None, "platforms"), {(n["kind"], n["node"], n["key"]) for n in result["notices"]})
        result = project({
            "platforms": [{"name": "vm", "host_vars": {"k": 1}}],
            "scenarios": [{"name": "a", "provisioner": {"inventory": None}}],
        }, SCHEMA)
        self.assertIn(("error", "a", "provisioner"), {(n["kind"], n["node"], n["key"]) for n in result["notices"]})


class Playbooks(unittest.TestCase):
    """Referenced playbooks resolve from the project root, whatever the scenarios directory."""

    def test_collection_shared_state_example(self):
        config = yaml.safe_load(example_source("collection-shared-state").read_text())
        self.assertEqual(referenced_playbooks(config), [
            "playbooks/molecule/converge.yml",
            "playbooks/molecule/create-default.yml",
            "playbooks/molecule/create.yml",
            "playbooks/molecule/destroy.yml",
            "playbooks/molecule/verify-app_config.yml",
            "playbooks/molecule/verify-app_users.yml",
            "playbooks/molecule/verify-default.yml",
        ])

    def test_both_keys_defaults_and_nested_children(self):
        config = {
            "defaults": {"provisioner": {"playbooks": {"prepare": "p.yml"}}},
            "scenarios": [{
                "name": "a",
                "playbooks": {"converge": "molecule/a/converge.yml"},
                "children": [{"name": "b", "children": [{"name": "c", "playbooks": {"verify": "./t/../v.yml"}}]}],
            }],
        }
        self.assertEqual(referenced_playbooks(config), [
            "molecule/a/converge.yml",
            "p.yml",
            "v.yml",
        ])

    def test_paths_outside_the_project_stay_visible(self):
        config = {"scenarios": [{"name": "a", "playbooks": {
            "verify": "../t.yml",
            "create": "/abs/c.yml",
            "prepare": "${MOLECULE_PROJECT_DIRECTORY}/x/../p.yml",
            "cleanup": "$MOLECULE_PROJECT_DIRECTORY/c.yml",
            "converge": "${HOME}/converge.yml",
        }}]}
        self.assertEqual(referenced_playbooks(config), ["${HOME}/converge.yml", "../t.yml", "/abs/c.yml", "c.yml", "p.yml"])

    def test_no_scenarios_no_playbooks(self):
        self.assertEqual(referenced_playbooks(None), [])
        self.assertEqual(referenced_playbooks({"defaults": {"playbooks": {"create": "c.yml"}}}), [])

    def test_example_playbooks_are_the_existing_files(self):
        found = example_playbooks("collection-shared-state")
        self.assertEqual(sorted(found), referenced_playbooks(
            yaml.safe_load(example_source("collection-shared-state").read_text())))
        root = example_source("collection-shared-state").parent
        self.assertEqual(found["playbooks/molecule/create.yml"],
                         (root / "playbooks" / "molecule" / "create.yml").read_text())

    def test_node_stage_hides_the_defaults_path(self):
        config = {
            "defaults": {"playbooks": {"converge": "shared.yml", "verify": "verify.yml"}},
            "scenarios": [
                {"name": "a", "playbooks": {"converge": "own.yml"}},
                {"name": "b", "provisioner": {"playbooks": {"verify": "b-verify.yml"}}},
            ],
        }
        self.assertEqual(referenced_playbooks(config), [
            "b-verify.yml",
            "own.yml",
            "shared.yml",
            "verify.yml",
        ])
        config["scenarios"][1]["playbooks"] = {"converge": "own.yml"}
        self.assertEqual(referenced_playbooks(config), ["b-verify.yml", "own.yml", "verify.yml"])

    def test_alias_and_provisioner_in_one_layer_follow_project(self):
        config = {"scenarios": [{"name": "a", "playbooks": {"verify": "x.yml"},
                                 "provisioner": {"playbooks": {"verify": "y.yml"}}}]}
        self.assertEqual(referenced_playbooks(config), ["y.yml"])

    def test_duplicate_names_and_empty_children(self):
        config = {"scenarios": [
            {"name": "a", "children": [], "playbooks": {"verify": "a.yml"}},
            {"name": "a", "playbooks": {"verify": "dup.yml"}},
            {"name": "b", "children": None},
        ]}
        self.assertEqual(referenced_playbooks(config), ["a.yml"])
        self.assertEqual(_steps(start_steps(config, 2)), {"a": 1, "b": 1})

    def test_playbooks_in_stays_inside_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            root = base / "project"
            (root / "playbooks").mkdir(parents=True)
            (root / "playbooks" / "ok.yml").write_text("ok\n")
            (base / "outside.yml").write_text("secret\n")
            (root / "playbooks" / "link.yml").symlink_to(base / "outside.yml")
            config = {"scenarios": [
                {"name": "a", "playbooks": {
                    "converge": "playbooks/ok.yml",
                    "verify": "../outside.yml",
                    "create": str(base / "outside.yml"),
                    "destroy": "playbooks/link.yml",
                    "prepare": "playbooks/../../outside.yml",
                    "cleanup": "${HOME}/outside.yml",
                }},
                {"name": "b", "playbooks": {"verify": "${MOLECULE_PROJECT_DIRECTORY}/playbooks/ok.yml"}},
            ]}
            self.assertEqual(playbooks_in(root, config), {"playbooks/ok.yml": "ok\n"})

    def test_convert_text_lists_them(self):
        result = convert_text(example_source("roles").read_text(), SCHEMA, "molecule")
        self.assertIn("playbooks/molecule/verify-motd.yml", result["playbooks"])


def _steps(order):
    return {s["name"]: s["step"] for s in order["scenarios"]}


class StartOrder(unittest.TestCase):
    """The step at which each scenario starts under the tree's scheduling rules."""

    def test_collection_shared_state_example(self):
        config = yaml.safe_load(example_source("collection-shared-state").read_text())
        order = start_steps(config)
        self.assertEqual(order["workers"], 1)
        self.assertEqual(order["scenarios"], [
            {"name": "default", "parent": None, "step": 1},
            {"name": "app_config", "parent": "default", "step": 2},
            {"name": "app_users", "parent": "default", "step": 3},
        ])

    def test_waves_wait_for_the_lower_wave_subtree(self):
        config = {"scenarios": [
            {"name": "a", "children": [
                {"name": "a1", "children": [{"name": "a1x"}]},
                {"name": "a2", "wave": 1},
            ]},
            {"name": "b"},
            {"name": "late", "wave": 1, "children": [{"name": "late1"}]},
        ]}
        self.assertEqual(_steps(start_steps(config, 9)), {
            "a": 1, "b": 1, "a1": 2, "a1x": 3, "a2": 4, "late": 5, "late1": 6,
        })

    def test_five_roots_two_workers(self):
        config = {"scenarios": [{"name": n} for n in "abcde"]}
        steps = _steps(start_steps(config, 2))
        self.assertEqual(steps, {"a": 1, "b": 1, "c": 2, "d": 2, "e": 3})
        counts = [list(steps.values()).count(s) for s in (1, 2, 3)]
        self.assertEqual(counts, [2, 2, 1])

    def test_waiting_scenarios_go_first_ready_first(self):
        config = {"scenarios": [{"name": "p", "children": [{"name": "c"}]}, {"name": "q"}, {"name": "r"}]}
        self.assertEqual(_steps(start_steps(config, 1)), {"p": 1, "q": 2, "r": 3, "c": 4})

    def test_workers_above_the_scenario_count_bind_nothing(self):
        config = {"scenarios": [{"name": "a"}, {"name": "b"}]}
        order = start_steps(config, 9)
        self.assertEqual(order["workers"], 9)
        self.assertEqual(order["scenarios"], start_steps(config, 2)["scenarios"])

    def test_one_worker_by_default(self):
        config = {"scenarios": [{"name": n} for n in "abc"]}
        order = start_steps(config)
        self.assertEqual(order["workers"], 1)
        self.assertEqual(_steps(order), {"a": 1, "b": 2, "c": 3})

    def test_wave_values(self):
        def run(wave):
            config = {"scenarios": [{"name": "a", "wave": wave}, {"name": "b"}]}
            notices = [(n["kind"], n["node"], n["key"]) for n in project(config, SCHEMA)["notices"]]
            return notices, _steps(start_steps(config, 2))
        self.assertEqual(run(1.0), ([("lost", "a", "wave")], {"a": 2, "b": 1}))
        self.assertEqual(run(-1), ([("lost", "a", "wave")], {"a": 1, "b": 2}))
        for bad in ("1", True, 1.5, None):
            with self.subTest(wave=bad):
                self.assertEqual(run(bad), ([("error", "a", "wave")], {"a": 1, "b": 1}))

    def test_workers_must_be_positive(self):
        with self.assertRaises(ValueError):
            start_steps({"scenarios": [{"name": "a"}]}, 0)

        for bad in (None, True, 1.5, "cpus"):
            with self.subTest(workers=bad), self.assertRaises(ValueError):
                start_steps({"scenarios": [{"name": "a"}]}, bad)

    def test_invalid_input_has_no_scenarios(self):
        self.assertEqual(start_steps(None), {"workers": 1, "scenarios": []})

    def test_cli_prints_the_order(self):
        source = str(example_source("collection-shared-state"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli_main([source, "--order", "--workers", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(),
                         "workers: 1 (--workers)\nstep 1: default\nstep 2: app_config\nstep 3: app_users\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_main([source, "--order"])
        self.assertEqual(out.getvalue(), "workers: 1\nstep 1: default\nstep 2: app_config\nstep 3: app_users\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_main([source, "--order", "--workers", "7"])
        self.assertEqual(out.getvalue(), "workers: 7 (--workers)\nstep 1: default\nstep 2: app_config, app_users\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "molecule.yml"
            path.write_text("---\nworkers: 2\nscenarios:\n  - name: a\n  - name: b\n  - name: c\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cli_main([str(path), "--order"])
            self.assertEqual(out.getvalue(), "workers: 2 (molecule.yml)\nstep 1: a, b\nstep 2: c\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cli_main([str(path), "--order", "--workers", "1"])
            self.assertEqual(out.getvalue(), "workers: 1 (--workers)\nstep 1: a\nstep 2: b\nstep 3: c\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli_main([source, "--order", "--workers", "cpus"])
        self.assertTrue(out.getvalue().startswith("workers: "), out.getvalue())
        self.assertIn("(--workers", out.getvalue())
        for argv, message in (([source, "--order", "--workers", "abc"], "must be an integer of at least 1"),
                              ([source, "--order", "--workers", "0"], "must be an integer of at least 1"),
                              ([source, "--order", "--destroy", "sometimes"], "invalid choice")):
            with self.subTest(argv=argv):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as raised:
                    cli_main(argv)
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(message, err.getvalue())
        self.assertEqual(order_text(start_steps({"scenarios": [{"name": n} for n in "abcde"]}, 2)),
                         "workers: 2\nstep 1: a, b\nstep 2: c, d\nstep 3: e\n")


class Workers(unittest.TestCase):
    """The run-level `workers` key, the `--workers` override and the checks today's Molecule makes."""

    def test_words_come_from_the_schema(self):
        self.assertEqual(sorted(workers_words(SCHEMA)), sorted(CPU_OFFSETS))
        self.assertEqual(SCHEMA["properties"]["workers"]["default"], 1)

    def test_precedence(self):
        config = {"workers": 3, "scenarios": [{"name": "a"}]}
        self.assertEqual(run_workers(config, SCHEMA), {"workers": 3, "requested": 3, "source": "file"})
        self.assertEqual(run_workers(config, SCHEMA, 2), {"workers": 2, "requested": 2, "source": "flag"})
        self.assertEqual(run_workers({"scenarios": []}, SCHEMA), {"workers": 1, "requested": 1, "source": "default"})
        self.assertEqual(run_workers(None, SCHEMA)["workers"], 1)

    def test_cpu_words_are_floored_at_one(self):
        self.assertEqual(run_workers({"workers": "cpus"}, SCHEMA, cpus=8)["workers"], 8)
        self.assertEqual(run_workers({"workers": "cpus-1"}, SCHEMA, cpus=8)["workers"], 7)
        self.assertEqual(run_workers({"workers": "cpus-1"}, SCHEMA, cpus=1)["workers"], 1)
        self.assertEqual(run_workers({"workers": "cpus"}, SCHEMA)["workers"], 1)

    def test_invalid_file_value_is_error_and_orders_at_the_default(self):
        for bad in (0, -1, True, 1.5, "all", None):
            with self.subTest(workers=bad):
                text = yaml.safe_dump({"workers": bad, "scenarios": [{"name": "a"}, {"name": "b"}]})
                result = convert_text(text, SCHEMA)
                self.assertIn(("error", None, "workers"),
                              {(n["kind"], n["node"], n["key"]) for n in result["notices"]})
                self.assertEqual(result["order"]["workers"], 1)
                self.assertEqual(result["order"]["source"], "default")

    def test_invalid_override_raises(self):
        with self.assertRaises(ValueError):
            convert_text("---\nscenarios:\n  - name: a\n", SCHEMA, workers=0)

    def test_file_value_is_lost_with_the_flag_to_pass(self):
        result = project({"workers": 4, "scenarios": [{"name": "a"}]}, SCHEMA)
        self.assertEqual([(n["kind"], n["key"]) for n in result["notices"]], [("lost", "workers")])
        self.assertIn("`--workers 4`", result["notices"][0]["message"])
        self.assertEqual(result["files"][0]["content"], {})

    def test_above_one_outside_a_collection_is_unsupported(self):
        text = "---\nworkers: 2\nscenarios:\n  - name: a\n"
        kinds = [(n["kind"], n["key"]) for n in convert_text(text, SCHEMA, "molecule")["notices"]]
        self.assertEqual(kinds, [("lost", "workers"), ("unsupported", "workers")])
        kinds = [(n["kind"], n["key"]) for n in convert_text(text, SCHEMA)["notices"]]
        self.assertEqual(kinds, [("lost", "workers")])
        kinds = [n["kind"] for n in convert_text(text, SCHEMA, "molecule", workers=1)["notices"]]
        self.assertEqual(kinds, ["lost"])

    def test_above_one_with_destroy_never_is_unsupported(self):
        text = "---\nscenarios:\n  - name: a\n"
        self.assertEqual(convert_text(text, SCHEMA, workers=1, destroy="never")["notices"], [])
        notices = convert_text(text, SCHEMA, workers=2, destroy="never")["notices"]
        self.assertEqual([n["kind"] for n in notices], ["unsupported"])
        self.assertIn("--destroy=never", notices[0]["message"])
        self.assertEqual(convert_text(text, SCHEMA, workers=2)["notices"], [])

    def test_cpus_above_one_counts(self):
        text = "---\nworkers: cpus\nscenarios:\n  - name: a\n"
        notices = convert_text(text, SCHEMA, "molecule", cpus=4)["notices"]
        self.assertEqual([n["kind"] for n in notices], ["lost", "unsupported"])
        notices = convert_text(text, SCHEMA, "molecule", cpus=1)["notices"]
        self.assertEqual([n["kind"] for n in notices], ["lost"])


if __name__ == "__main__":
    unittest.main()
