"""Verify host isolation, credential handling, and preservation on sync failures."""

import argparse
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
loader = importlib.machinery.SourceFileLoader("private_sync", str(ROOT / ".local/bin/private-sync"))
spec = importlib.util.spec_from_loader(loader.name, loader)
sync = importlib.util.module_from_spec(spec)
loader.exec_module(sync)


class PrivateSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ssh = self.root / "ssh"
        self.stage = self.root / "stage"
        self.state = self.root / "state"
        for path in (self.ssh, self.stage, self.state):
            path.mkdir()
        self.live = self.ssh / "config.shared"
        self.live.write_text("Host example\n  User original\n")
        self.original = self.live.read_bytes()
        self.args = argparse.Namespace(resync=None, dry_run=False)

    def run_sync(self, action=None):
        def run(command, **kwargs):
            if command[:2] == ["rclone", "bisync"]:
                self.assertEqual(command[3], "private_sync:ssh")
                self.assertEqual(kwargs["env"]["RCLONE_CONFIG_PRIVATE_SYNC_REMOTE"], "gdrive:private-sync")
                self.assertNotIn("secret-password", command)
                if action:
                    action()
            return subprocess.CompletedProcess(command, 0)

        with patch.object(sync, "capture", side_effect=[
            "session", '{"type":1,"name":"private-sync (rclone)","login":{"username":"secret-password","password":"secret-salt"}}',
            "obscured-password", "obscured-salt",
        ]), patch.object(sync.subprocess, "run", side_effect=run) as runner:
            try:
                sync.sync(self.args, self.stage, self.state, self.live)
            finally:
                self.assertEqual(runner.call_args.args[0], ["bw", "lock"])

    def test_nonpersonal_stops_before_subprocess_or_home_access(self):
        with patch.object(sync, "personal", return_value=False), patch.object(sync.subprocess, "run") as run:
            self.assertEqual(sync.main(), 2)
            run.assert_not_called()

    def test_allowlist_exact_short_host(self):
        (self.root / "personal-hosts").write_text("personal\n")
        with patch.object(sync, "ROOT", self.root), patch.object(sync.socket, "gethostname", return_value="personal.local"):
            self.assertTrue(sync.personal())
        with patch.object(sync, "ROOT", self.root), patch.object(sync.socket, "gethostname", return_value="personal-other"):
            self.assertFalse(sync.personal())

    def test_success_installs_remote_with_private_mode(self):
        self.run_sync(lambda: (self.stage / "config.shared").write_text("Host remote\n"))
        self.assertEqual(self.live.read_text(), "Host remote\n")
        self.assertEqual(self.live.stat().st_mode & 0o777, 0o600)

    def test_conflict_preserves_active_configuration(self):
        with self.assertRaisesRegex(ValueError, "sync conflict"):
            self.run_sync(lambda: (self.stage / "config.shared.conflict1").write_text("conflict"))
        self.assertEqual(self.live.read_bytes(), self.original)

    def test_failure_preserves_active_configuration(self):
        def fail():
            raise subprocess.CalledProcessError(1, ["rclone", "bisync"])
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_sync(fail)
        self.assertEqual(self.live.read_bytes(), self.original)

    def test_concurrent_edit_preserved(self):
        with self.assertRaisesRegex(ValueError, "changed during sync"):
            self.run_sync(lambda: self.live.write_text("concurrent edit"))
        self.assertEqual(self.live.read_text(), "concurrent edit")

    def test_dry_run_does_not_install(self):
        self.args.dry_run = True
        self.run_sync(lambda: (self.stage / "config.shared").write_text("remote"))
        self.assertEqual(self.live.read_bytes(), self.original)

    def test_symlink_refused(self):
        self.live.unlink()
        self.live.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(ValueError, "symlink"), patch.object(sync, "capture") as capture:
            sync.sync(self.args, self.stage, self.state, self.live)
        capture.assert_not_called()

    def test_prepare_preserves_original_and_local(self):
        self.live.unlink()
        (self.ssh / "config").write_bytes(self.original)
        (self.ssh / "config.local").write_text("Host local\n")
        sync.prepare(self.ssh)
        sync.prepare(self.ssh)
        self.assertEqual(self.live.read_bytes(), self.original)
        self.assertEqual((self.ssh / "config.before-private-sync").read_bytes(), self.original)
        self.assertEqual((self.ssh / "config.local").read_text(), "Host local\n")

    def test_prepare_after_pull_preserves_shared_and_local(self):
        local = self.ssh / "config.local"
        local.write_text("Host local\n")
        sync.prepare(self.ssh)
        config = self.ssh / "config"
        self.assertEqual(config.read_text(), "Include config.local\nHost *\n    Include config.shared\n")
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        sync.prepare(self.ssh)
        self.assertEqual(self.live.read_bytes(), self.original)
        self.assertEqual(local.read_text(), "Host local\n")
        self.assertFalse((self.ssh / "config.before-private-sync").exists())

    def test_prepare_without_usable_shared_requires_pull(self):
        self.live.unlink()
        for empty_file in (False, True):
            with self.subTest(empty_file=empty_file):
                if empty_file:
                    self.live.touch()
                with self.assertRaisesRegex(ValueError, "--resync vault"):
                    sync.prepare(self.ssh)
                self.assertFalse((self.ssh / "config").exists())

    def test_prepare_after_pull_refuses_existing_backup(self):
        backup = self.ssh / "config.before-private-sync"
        backup.write_text("old config")
        with self.assertRaisesRegex(ValueError, "review migration manually"):
            sync.prepare(self.ssh)
        self.assertFalse((self.ssh / "config").exists())
        self.assertEqual(backup.read_text(), "old config")
        self.assertEqual(self.live.read_bytes(), self.original)

    def test_prepare_after_pull_refuses_symlink_destination(self):
        (self.ssh / "config").symlink_to(self.root / "missing-config")
        with self.assertRaisesRegex(ValueError, "symlink"):
            sync.prepare(self.ssh)
        self.assertEqual(self.live.read_bytes(), self.original)

    def test_real_crypt_roundtrip_and_conflict(self):
        remote = self.root / "encrypted"
        real_run = subprocess.run

        def run(command, **kwargs):
            if command[0] == "bw":
                output = {
                    "unlock": "test-session",
                    "get": '{"type":1,"name":"private-sync (rclone)","login":{"username":"test-password","password":"test-salt"}}',
                }.get(command[1], "")
                return subprocess.CompletedProcess(command, 0, stdout=output)
            return real_run(command, **kwargs)

        self.args.resync = "local"
        with patch.object(sync, "REMOTE", str(remote)), patch.object(sync.subprocess, "run", side_effect=run):
            sync.sync(self.args, self.stage, self.state, self.live)
            self.assertFalse(any(b"Host example" in path.read_bytes() for path in remote.rglob("*") if path.is_file()))
            other_stage = self.root / "other-stage"
            other_state = self.root / "other-state"
            other_live = self.root / "other-config"
            other_stage.mkdir()
            other_state.mkdir()
            self.args.resync = "vault"
            sync.sync(self.args, other_stage, other_state, other_live)
            self.assertEqual(other_live.read_bytes(), self.original)
            self.args.resync = None
            other_live.write_text("Host remote-change\n")
            sync.sync(self.args, other_stage, other_state, other_live)
            sync.sync(self.args, self.stage, self.state, self.live)
            self.assertEqual(self.live.read_text(), "Host remote-change\n")
            other_live.write_text("Host remote-conflict\n")
            sync.sync(self.args, other_stage, other_state, other_live)
            self.live.write_text("Host local-conflict\n")
            with self.assertRaisesRegex(ValueError, "sync conflict"):
                sync.sync(self.args, self.stage, self.state, self.live)
            self.assertEqual(self.live.read_text(), "Host local-conflict\n")


class FishGateTest(unittest.TestCase):
    def test_unknown_host_never_calls_bw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            uname = root / "uname"
            uname.write_text("#!/bin/sh\nprintf '%s\\n' unknown-test-host\n")
            uname.chmod(0o755)
            result = subprocess.run([
                "fish", "--no-config", "-c",
                f"source {ROOT}/.config/fish/functions/is_personal.fish; "
                f"source {ROOT}/.config/fish/functions/secret-sync.fish; "
                "function bw; echo VAULT_CALLED; end; secret-sync pull --yes",
            ], env={**os.environ, "PATH": f"{root}:{os.environ['PATH']}"}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("VAULT_CALLED", result.stdout)
            self.assertIn("non-personal", result.stderr)


if __name__ == "__main__":
    unittest.main()
