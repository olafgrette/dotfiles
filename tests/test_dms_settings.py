import importlib.util
from importlib.machinery import SourceFileLoader
import json
import subprocess
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
    def test_legacy_local_overrides_move_without_overwriting_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            old = repo / ".config/DankMaterialShell"
            new = repo / ".config/dms"
            old.mkdir(parents=True)
            new.mkdir()
            settings = '{"privatePreference": true}\n'
            (old / "settings.local.json").write_text(settings)
            (old / "plugins.lock.local.json").write_text('{"plugins": {}}\n')
            (new / "plugins.lock.local.json").write_text('{"plugins": {"local": {}}}\n')
            with self.assertRaisesRegex(ValueError, "migration conflict"):
                MODULE.migrate_local_overrides(repo)
            self.assertEqual((old / "settings.local.json").read_text(), settings)
            self.assertFalse((new / "settings.local.json").exists())
            self.assertEqual((new / "plugins.lock.local.json").read_text(),
                             '{"plugins": {"local": {}}}\n')
            (new / "plugins.lock.local.json").unlink()
            MODULE.migrate_local_overrides(repo)
            MODULE.migrate_local_overrides(repo)
            self.assertEqual((new / "settings.local.json").read_text(), settings)
            self.assertEqual((new / "plugins.lock.local.json").read_text(), '{"plugins": {}}\n')
            self.assertEqual(list(old.iterdir()), [])

    def plugin_args(self, root):
        return SimpleNamespace(
            live=root / "config/dms/settings.json",
            patch=root / "shared/settings.patch.json",
            local_patch=root / "shared/settings.local.json",
            settings_only=False,
        )

    def test_plugin_capture_excludes_local_entries_and_keeps_hidden_shared_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.plugin_args(Path(directory))
            MODULE.atomic_json(args.live, {"preference": True})
            shared = {"lockfileVersion": 1, "plugins": {"common": {"commit": "old"}}}
            local = {"lockfileVersion": 1, "plugins": {
                "common": {"commit": "override"}, "private": {"commit": "private"},
            }}
            target = args.patch.with_name("plugins.lock.json")
            MODULE.atomic_json(target, shared)
            MODULE.atomic_json(args.local_patch.with_name("plugins.lock.local.json"), local)

            def export(command, **kwargs):
                self.assertEqual(command[:4], ["dms", "plugins", "lock", "--output"])
                self.assertEqual(kwargs["env"]["XDG_CONFIG_HOME"], str(args.live.parent.parent))
                MODULE.atomic_json(Path(command[4]), {"lockfileVersion": 1, "plugins": {
                    **local["plugins"], "new": {"commit": "new"},
                }})

            with patch.object(MODULE.subprocess, "run", side_effect=export):
                MODULE.capture(args)
            self.assertEqual(MODULE.load_json(target)["plugins"], {
                "common": {"commit": "old"}, "new": {"commit": "new"},
            })

    def test_restore_overrides_whole_entries_before_settings_without_pruning(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.plugin_args(Path(directory))
            MODULE.atomic_json(args.live, {"preference": False})
            MODULE.atomic_json(args.patch, {"preference": True})
            MODULE.atomic_json(args.patch.with_name("plugins.lock.json"), {
                "lockfileVersion": 1, "plugins": {"common": {"path": "old", "repo": "shared"}},
            })
            MODULE.atomic_json(args.local_patch.with_name("plugins.lock.local.json"), {
                "lockfileVersion": 1, "plugins": {"common": {"repo": "local"}},
            })

            def restore(command, **kwargs):
                self.assertEqual(command[:3], ["dms", "plugins", "restore"])
                self.assertEqual(len(command), 4)
                self.assertEqual(MODULE.load_json(Path(command[3]))["plugins"],
                                 {"common": {"repo": "local"}})
                self.assertEqual(MODULE.load_json(args.live), {"preference": False})

            with patch.object(MODULE.subprocess, "run", side_effect=restore) as run:
                MODULE.apply(args)
                run.assert_called_once()
            self.assertEqual(MODULE.effective_settings(args), {"preference": True})

    def test_plugin_failures_preserve_settings_and_shared_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.plugin_args(Path(directory))
            MODULE.atomic_json(args.live, {"preference": False})
            MODULE.atomic_json(args.patch, {"preference": True})
            target = args.patch.with_name("plugins.lock.json")
            lock = {"lockfileVersion": 1, "plugins": {}}
            MODULE.atomic_json(target, lock)
            with patch.object(MODULE.subprocess, "run",
                              side_effect=subprocess.CalledProcessError(1, ["dms"])):
                for operation in (MODULE.capture, MODULE.apply):
                    with self.assertRaises(subprocess.CalledProcessError):
                        operation(args)
                    self.assertEqual(MODULE.load_json(args.live), {"preference": False})
                    self.assertEqual(MODULE.load_json(args.patch), {"preference": True})
                    self.assertEqual(MODULE.load_json(target), lock)
            target.write_text('{"lockfileVersion": 2, "plugins": {}}')
            with self.assertRaisesRegex(ValueError, "version 1"):
                MODULE.apply(args)
            self.assertEqual(MODULE.load_json(args.live), {"preference": False})

    def test_settings_only_skips_plugins_and_absent_locks_need_no_dms(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.plugin_args(Path(directory))
            MODULE.atomic_json(args.live, {})
            with patch.object(MODULE.subprocess, "run") as run:
                MODULE.apply(args)
                args.patch.parent.mkdir(parents=True)
                args.patch.with_name("plugins.lock.json").write_text("invalid")
                args.settings_only = True
                MODULE.capture(args)
                MODULE.apply(args)
                run.assert_not_called()

    def test_atomic_json_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            self.assertTrue(MODULE.atomic_json(path, {"b": 2, "a": 1}))
            first = path.read_bytes()
            self.assertFalse(MODULE.atomic_json(path, {"a": 1, "b": 2}))
            self.assertEqual(path.read_bytes(), first)

    def test_native_precedence_and_private_drop_ins_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.plugin_args(Path(directory))
            args.settings_only = True
            MODULE.atomic_json(args.live, {"preference": "base", "newGuiSetting": True})
            MODULE.atomic_json(args.patch, {"preference": "shared", "nested": {"shared": True}})
            MODULE.atomic_json(args.local_patch, {"nested": {"local": True}})
            other = args.live.parent / "config.d/99-work.local.json"
            MODULE.atomic_json(other, {"preference": "private", "privateOnly": True})
            MODULE.apply(args)
            self.assertEqual(MODULE.effective_settings(args), {
                "preference": "private", "nested": {"local": True},
                "privateOnly": True, "newGuiSetting": True,
            })
            MODULE.capture(args)
            self.assertEqual(MODULE.load_json(args.patch), {
                "preference": "shared", "nested": {"shared": True}, "newGuiSetting": True,
            })
            self.assertEqual(MODULE.load_json(other), {"preference": "private", "privateOnly": True})
            before = args.live.read_bytes()
            other.write_text("invalid")
            with patch.object(MODULE.subprocess, "run") as run:
                for operation in (MODULE.capture, MODULE.apply):
                    with self.assertRaises(ValueError):
                        operation(args)
                run.assert_not_called()
            self.assertEqual(args.live.read_bytes(), before)

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
                settings_only=True,
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
                settings_only=True,
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
                settings_only=True,
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
                settings_only=True,
                live=root / "settings.json", patch=root / "settings.patch.json",
                local_patch=root / "settings.local.json",
            )
            MODULE.apply(args)
            self.assertFalse((root / "clsettings.json").exists())
            self.assertFalse((root / "plugin_settings.json").exists())

    def test_native_migration_gui_capture_and_shared_key_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = self.plugin_args(root)
            args.settings_only = True
            shared = {"muxType": "zellij", "acLockTimeout": 300,
                      "nested": {"shared": True}, "localSetting": "shared"}
            MODULE.atomic_json(args.patch, shared)
            MODULE.atomic_json(args.local_patch, {"localSetting": "override"})
            MODULE.atomic_json(args.live, {
                "configVersion": 42, "displayProfiles": {"machine": {}},
                "muxType": "tmux", "acLockTimeout": 200,
                "showSeconds": True, "nested": {"obsolete": True},
            })
            MODULE.apply(args)
            base = {"configVersion": 42, "displayProfiles": {"machine": {}}, "showSeconds": True}
            self.assertEqual(MODULE.load_json(args.live), base)
            self.assertEqual(MODULE.effective_settings(args),
                             {**base, **shared, "localSetting": "override"})
            shared_live = args.live.parent / "config.d" / MODULE.SHARED_DROPIN
            before = shared_live.stat()
            MODULE.apply(args)
            self.assertEqual(shared_live.stat().st_ino, before.st_ino)
            self.assertEqual(shared_live.stat().st_mtime_ns, before.st_mtime_ns)
            # Dux writes edits to the last file owning each top-level key.
            gui = MODULE.load_json(shared_live)
            gui["muxType"] = "tmux"
            del gui["acLockTimeout"]
            MODULE.atomic_json(shared_live, gui)
            MODULE.capture(args)
            captured = {**shared, "muxType": "tmux", "showSeconds": True}
            del captured["acLockTimeout"]
            self.assertEqual(MODULE.load_json(args.patch), captured)
            MODULE.apply(args)
            # An adopted base preference now belongs to the native shared file.
            self.assertNotIn("showSeconds", MODULE.load_json(args.live))
            MODULE.atomic_json(args.patch, {})
            MODULE.apply(args)
            self.assertEqual(MODULE.effective_settings(args), {
                "configVersion": 42, "displayProfiles": {"machine": {}},
                "localSetting": "override",
            })

    def test_apply_clears_auxiliary_preferences_absent_from_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                settings_only=True,
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
            args = self.plugin_args(root)
            args.settings_only = True
            live = {
                "configVersion": 42, "dmsWindowsFloatingSeeded": ["hyprland"],
                "displayProfiles": {"local": {}},
                "barConfigs": [{"id": "main", "spacing": 4,
                                "screenPreferences": ["local-output"], "showOnLastDisplay": False}],
                "dockConfigs": [{"id": "dock", "enabled": False,
                                 "screenPreferences": ["local-output"], "showOnLastDisplay": True}],
                "desktopWidgetInstances": [{"id": "monitor", "positions": {"local-output": {}},
                                            "config": {"displayPreferences": ["local-output"],
                                                       "gpuPciId": "local-gpu", "showCpu": True}}],
            }
            MODULE.atomic_json(args.live, live)
            MODULE.capture(args)
            captured = MODULE.load_json(args.patch)
            self.assertEqual(captured, {
                "barConfigs": [{"id": "main", "spacing": 4}],
                "dockConfigs": [{"id": "dock", "enabled": False}],
                "desktopWidgetInstances": [{"id": "monitor", "config": {"showCpu": True}}],
            })
            MODULE.apply(args)
            self.assertEqual(MODULE.effective_settings(args), live)
            shared_live = args.live.parent / "config.d" / MODULE.SHARED_DROPIN
            gui = MODULE.load_json(shared_live)
            gui["barConfigs"][0]["screenPreferences"] = ["another-output"]
            MODULE.atomic_json(shared_live, gui)
            captured["barConfigs"].insert(0, {"id": "extra", "spacing": 2})
            captured["barConfigs"][1]["spacing"] = 8
            captured["dockConfigs"].insert(0, {"id": "extra", "enabled": False})
            captured["dockConfigs"][1]["enabled"] = True
            captured["desktopWidgetInstances"][0]["config"]["showCpu"] = False
            MODULE.atomic_json(args.patch, captured)
            MODULE.apply(args)
            updated = MODULE.effective_settings(args)
            self.assertEqual(updated["dockConfigs"], [
                {"id": "extra", "enabled": False},
                {"id": "dock", "enabled": True, "screenPreferences": ["local-output"],
                 "showOnLastDisplay": True},
            ])
            self.assertEqual(updated["barConfigs"], [
                {"id": "extra", "spacing": 2},
                {"id": "main", "spacing": 8, "screenPreferences": ["another-output"],
                 "showOnLastDisplay": False},
            ])
            self.assertEqual(updated["desktopWidgetInstances"][0]["config"], {
                "displayPreferences": ["local-output"], "gpuPciId": "local-gpu", "showCpu": False,
            })
            # A native local override replaces the entire array, as Dux specifies.
            override = [{"id": "main", "spacing": 6, "screenPreferences": ["override-output"]}]
            MODULE.atomic_json(args.local_patch, {"barConfigs": override})
            MODULE.apply(args)
            self.assertEqual(MODULE.effective_settings(args)["barConfigs"], override)
            MODULE.capture(args)
            self.assertEqual(MODULE.load_json(args.patch)["barConfigs"], captured["barConfigs"])
            # A fresh host receives portable instances without this host's selectors.
            args.live = root / "fresh/dms/settings.json"
            args.local_patch = root / "fresh/settings.local.json"
            MODULE.apply(args)
            self.assertEqual(MODULE.effective_settings(args), captured)

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
