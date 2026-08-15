import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import sys
import tempfile
import unittest
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
            )
            self.assertEqual(MODULE.capture(args), 0)
            self.assertEqual(json.loads(patch.read_text()), {"changed": 2})


if __name__ == "__main__":
    unittest.main()
