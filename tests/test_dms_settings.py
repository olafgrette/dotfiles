import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


SCRIPT = Path(__file__).parents[1] / ".local/bin/dms-settings"
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_loader("dms_settings", SourceFileLoader("dms_settings", str(SCRIPT)))
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DmsSettingsTest(unittest.TestCase):
    def test_recursive_three_way_preserves_local_conflict(self):
        old = {"same": 1, "remote": 1, "local": 1, "nested": {"a": 1, "b": 1}}
        live = {"same": 1, "remote": 1, "local": 2, "nested": {"a": 2, "b": 1}}
        new = {"same": 1, "remote": 2, "local": 3, "nested": {"a": 1, "b": 2}}
        self.assertEqual(
            MODULE.three_way(old, live, new),
            {"same": 1, "remote": 2, "local": 2, "nested": {"a": 2, "b": 2}},
        )

    def test_three_way_applies_removal_only_when_unchanged(self):
        self.assertEqual(MODULE.three_way({"a": 1}, {"a": 1}, {}), {})
        self.assertEqual(MODULE.three_way({"a": 1}, {"a": 2}, {}), {"a": 2})

    def test_arrays_are_atomic(self):
        self.assertEqual(MODULE.three_way([1], [1], [2]), [2])
        self.assertEqual(MODULE.three_way([1], [3], [2]), [3])

    def test_default_parser_handles_literals_and_enums(self):
        source = """
        enum Speed { Slow, Fast = 4, Faster }
        property bool enabled: true
        property string name: "dms"
        property int speed: SettingsData.Speed.Faster
        property var empty: ({})
        property int computed: Other.value
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SettingsData.qml"
            path.write_text(source)
            self.assertEqual(
                MODULE.parse_defaults(path),
                {"enabled": True, "name": "dms", "speed": 5, "empty": {}},
            )

    def test_find_defaults_uses_embedded_runtime_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            defaults = runtime / "danklinux-shell/current/Common/SettingsData.qml"
            defaults.parent.mkdir(parents=True)
            defaults.write_text("property bool enabled: true\n")
            with patch.dict(MODULE.os.environ, {"XDG_RUNTIME_DIR": str(runtime)}, clear=True):
                self.assertEqual(MODULE.find_defaults(None), defaults)

    def test_atomic_json_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            self.assertTrue(MODULE.atomic_json(path, {"b": 2, "a": 1}))
            first = path.read_bytes()
            self.assertFalse(MODULE.atomic_json(path, {"a": 1, "b": 2}))
            self.assertEqual(path.read_bytes(), first)

    def test_color_object_equals_hex_default(self):
        color = {"r": 1, "g": 1, "b": 1, "a": 1, "valid": True}
        self.assertTrue(MODULE.settings_equal(color, "#ffffff"))
        self.assertFalse(MODULE.settings_equal({**color, "r": 0.5}, "#ffffff"))

    def test_capture_selects_nondefault_unblocked_settings(self):
        source = """
        property bool unchanged: true
        property int changed: 1
        property string activeDisplayProfile: ""
        property int localOnly: 1
        property int unresolved: Other.value
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            defaults = root / "SettingsData.qml"
            live = root / "live.json"
            patch = root / "patch.json"
            local_patch = root / "local.json"
            defaults.write_text(source)
            MODULE.atomic_json(live, {
                "unchanged": True,
                "changed": 2,
                "activeDisplayProfile": "machine",
                "localOnly": 2,
                "unresolved": 2,
            })
            MODULE.atomic_json(local_patch, {"localOnly": 2})
            args = SimpleNamespace(
                live=live,
                patch=patch,
                local_patch=local_patch,
                defaults=defaults,
                baseline=root / "baseline.json",
            )
            self.assertEqual(MODULE.capture(args), 0)
            self.assertEqual(json.loads(patch.read_text()), {"changed": 2, "unresolved": 2})

    def test_auxiliary_capture_and_apply_preserves_gui_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            shared = root / "shared"
            config.mkdir()
            shared.mkdir()
            defaults = root / "SettingsData.qml"
            defaults.write_text("property bool enabled: true\n")
            args = SimpleNamespace(
                live=config / "settings.json",
                patch=shared / "settings.patch.json",
                local_patch=shared / "settings.local.json",
                baseline=root / "state/baseline.json",
                defaults=defaults,
            )
            MODULE.atomic_json(args.live, {"enabled": True, "newPreference": 42})
            MODULE.atomic_json(config / "clsettings.json", {"maxHistory": 50000, "disabled": False})
            MODULE.atomic_json(config / "plugin_settings.json", {"example": {"enabled": True}})
            MODULE.atomic_json(shared / "clsettings.local.json", {"disabled": True})
            MODULE.capture(args)
            self.assertEqual(MODULE.load_json(args.patch), {"newPreference": 42})
            self.assertEqual(MODULE.load_json(shared / "clsettings.patch.json"), {"maxHistory": 50000})
            self.assertEqual(MODULE.load_json(shared / "plugin_settings.patch.json"),
                             {"example": {"enabled": True}})
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(config / "clsettings.json"),
                             {"maxHistory": 50000, "disabled": True})
            MODULE.atomic_json(config / "clsettings.json", {"maxHistory": 1000, "disabled": True})
            MODULE.atomic_json(shared / "clsettings.patch.json", {"maxHistory": 20000})
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(config / "clsettings.json")["maxHistory"], 1000)
            # A fresh machine receives all captured preference files.
            args.live = root / "fresh/settings.json"
            args.baseline = root / "fresh-state/baseline.json"
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live.with_name("clsettings.json")),
                             {"maxHistory": 20000, "disabled": True})
            self.assertEqual(MODULE.load_json(args.live.with_name("plugin_settings.json")),
                             {"example": {"enabled": True}})

    def test_malformed_auxiliary_file_does_not_partially_capture_or_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            defaults = root / "SettingsData.qml"
            defaults.write_text("property bool enabled: true\n")
            args = SimpleNamespace(
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json", baseline=root / "baseline.json",
                defaults=defaults,
            )
            MODULE.atomic_json(args.live, {"enabled": False})
            MODULE.atomic_json(args.patch, {"enabled": True})
            clipboard = root / "clsettings.json"
            clipboard.write_text("invalid json")
            with self.assertRaises(ValueError):
                MODULE.capture(args)
            self.assertEqual(MODULE.load_json(args.patch), {"enabled": True})
            MODULE.atomic_json(root / "clsettings.patch.json", {"maxHistory": 50000})
            with self.assertRaises(ValueError):
                MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live), {"enabled": False})
            self.assertFalse(args.baseline.exists())

    def test_absent_auxiliary_files_are_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json", baseline=root / "baseline.json",
            )
            MODULE.apply(args)
            self.assertFalse((root / "clsettings.json").exists())
            self.assertFalse((root / "plugin_settings.json").exists())

    def test_offer_commit_stages_and_commits_only_patch(self):
        completed = type("Completed", (), {"stdout": " M settings.patch.json\n"})()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            tracked_patch = repo / "settings.patch.json"
            tracked_patch.write_text("{}\n")
            with (
                patch.object(MODULE.subprocess, "run", return_value=completed) as run,
                patch.object(MODULE.sys.stdin, "isatty", return_value=True),
                patch("builtins.input", return_value="y"),
            ):
                MODULE.offer_commit(repo, tracked_patch)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0][:2], ["git", "status"])
            self.assertEqual(commands[1][:2], ["git", "diff"])
            self.assertEqual(commands[2], ["git", "add", "--", "settings.patch.json"])
            self.assertEqual(commands[3][0:3], ["git", "commit", "--only"])


if __name__ == "__main__":
    unittest.main()
