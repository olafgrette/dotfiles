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
    def test_atomic_json_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            self.assertTrue(MODULE.atomic_json(path, {"b": 2, "a": 1}))
            first = path.read_bytes()
            self.assertFalse(MODULE.atomic_json(path, {"a": 1, "b": 2}))
            self.assertEqual(path.read_bytes(), first)

    def test_capture_reads_sparse_json_without_shell_or_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "live.json"
            patch = root / "patch.json"
            local_patch = root / "local.json"
            MODULE.atomic_json(live, {
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
            )
            self.assertEqual(MODULE.capture(args), 0)
            self.assertEqual(json.loads(patch.read_text()), {"changed": 2, "unresolved": 2})

    def test_auxiliary_capture_and_apply_replaces_gui_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            shared = root / "shared"
            config.mkdir()
            shared.mkdir()
            args = SimpleNamespace(
                live=config / "settings.json",
                patch=shared / "settings.patch.json",
                local_patch=shared / "settings.local.json",
            )
            MODULE.atomic_json(args.live, {"newPreference": 42})
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
            self.assertEqual(MODULE.load_json(config / "clsettings.json")["maxHistory"], 20000)
            # A fresh machine receives all captured preference files.
            args.live = root / "fresh/settings.json"
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live.with_name("clsettings.json")),
                             {"maxHistory": 20000, "disabled": True})
            self.assertEqual(MODULE.load_json(args.live.with_name("plugin_settings.json")),
                             {"example": {"enabled": True}})

    def test_malformed_auxiliary_file_does_not_partially_capture_or_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json",
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

    def test_absent_auxiliary_files_are_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json",
            )
            MODULE.apply(args)
            self.assertFalse((root / "clsettings.json").exists())
            self.assertFalse((root / "plugin_settings.json").exists())

    def test_apply_replaces_portable_settings_and_capture_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json",
            )
            shared = {"muxType": "zellij", "acLockTimeout": 300,
                      "barConfigs": [{"id": "default", "spacing": 4}],
                      "nested": {"shared": True}, "localSetting": "shared"}
            MODULE.atomic_json(args.patch, shared)
            MODULE.atomic_json(args.local_patch, {"localSetting": "override"})
            MODULE.atomic_json(args.live, {
                "configVersion": 18, "displayProfiles": {"machine": {}},
                "barConfigs": [{"id": "default", "spacing": 0,
                                "screenPreferences": ["local-output"]}],
                "showSeconds": True, "nested": {"extra": True},
            })
            MODULE.apply(args)
            expected = {**shared, "configVersion": 18, "displayProfiles": {"machine": {}},
                        "localSetting": "override", "barConfigs": [
                            {"id": "default", "spacing": 4,
                             "screenPreferences": ["local-output"]}]}
            self.assertEqual(MODULE.load_json(args.live), expected)
            first_stat = args.live.stat()
            MODULE.apply(args)
            self.assertEqual(args.live.stat().st_ino, first_stat.st_ino)
            self.assertEqual(args.live.stat().st_mtime_ns, first_stat.st_mtime_ns)
            MODULE.capture(args)
            self.assertEqual(MODULE.load_json(args.patch), shared)
            # Capture includes GUI additions, edits, and resets to default.
            gui = MODULE.load_json(args.live)
            del gui["acLockTimeout"]
            gui["muxType"] = "tmux"
            gui["showSeconds"] = True
            MODULE.atomic_json(args.live, gui)
            MODULE.capture(args)
            captured = {**shared, "muxType": "tmux", "showSeconds": True}
            del captured["acLockTimeout"]
            self.assertEqual(MODULE.load_json(args.patch), captured)
            # Removing portable keys in Git resets them, even with live GUI edits.
            MODULE.atomic_json(args.patch, {})
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live), {
                "configVersion": 18, "displayProfiles": {"machine": {}},
                "localSetting": "override",
            })

    def test_apply_clears_auxiliary_preferences_absent_from_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json",
            )
            MODULE.atomic_json(root / "clsettings.json", {"maxHistory": 100000})
            MODULE.atomic_json(root / "plugin_settings.json", {"example": {"enabled": True}})
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(root / "clsettings.json"), {})
            self.assertEqual(MODULE.load_json(root / "plugin_settings.json"), {})

    def test_nested_machine_fields_stay_local_across_capture_and_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json",
            )
            live = {
                "configVersion": 17,
                "displayProfiles": {"local": {}},
                "barConfigs": [{"id": "main", "spacing": 4,
                                "screenPreferences": ["local-output"], "showOnLastDisplay": False}],
                "desktopWidgetInstances": [{"id": "monitor", "positions": {"local-output": {}},
                                            "config": {"displayPreferences": ["local-output"],
                                                       "gpuPciId": "local-gpu", "showCpu": True}}],
            }
            MODULE.atomic_json(args.live, live)
            MODULE.capture(args)
            captured = MODULE.load_json(args.patch)
            self.assertEqual(captured, {
                "barConfigs": [{"id": "main", "spacing": 4}],
                "desktopWidgetInstances": [{"id": "monitor", "config": {"showCpu": True}}],
            })
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live), live)
            # Local monitor changes must not block a shared appearance update.
            live["barConfigs"][0]["screenPreferences"] = ["another-output"]
            MODULE.atomic_json(args.live, live)
            captured["barConfigs"].insert(0, {"id": "extra", "spacing": 2})
            captured["barConfigs"][1]["spacing"] = 8
            captured["desktopWidgetInstances"][0]["config"]["showCpu"] = False
            MODULE.atomic_json(args.patch, captured)
            MODULE.apply(args)
            updated = MODULE.load_json(args.live)
            self.assertEqual(updated["barConfigs"], [
                {"id": "extra", "spacing": 2},
                {"id": "main", "spacing": 8, "screenPreferences": ["another-output"],
                 "showOnLastDisplay": False},
            ])
            self.assertEqual(updated["desktopWidgetInstances"][0]["config"], {
                "displayPreferences": ["local-output"], "gpuPciId": "local-gpu", "showCpu": False,
            })
            # Local appearance overrides also retain existing monitor assignments.
            MODULE.atomic_json(args.local_patch, {"barConfigs": [
                {"id": "main", "spacing": 6},
            ]})
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live)["barConfigs"], [
                {"id": "main", "spacing": 6, "screenPreferences": ["another-output"],
                 "showOnLastDisplay": False},
            ])
            # Explicit local overrides can still select a monitor.
            MODULE.atomic_json(args.local_patch, {"barConfigs": [
                {"id": "main", "spacing": 8, "screenPreferences": ["override-output"]},
            ]})
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live)["barConfigs"][0]["screenPreferences"],
                             ["override-output"])
            gui = MODULE.load_json(args.live)
            gui["barConfigs"][0]["screenPreferences"] = ["gui-output"]
            MODULE.atomic_json(args.live, gui)
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live)["barConfigs"][0]["screenPreferences"],
                             ["override-output"])
            # A new host receives portable instances, never this host's selectors.
            args.live = root / "fresh/settings.json"
            args.local_patch = root / "fresh/settings.local.json"
            MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live), captured)

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
