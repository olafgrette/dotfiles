"""Exercise update decisions against local Git repositories, without network access."""

import fcntl
import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_loader(
    "dotfiles_update", SourceFileLoader("dotfiles_update", str(ROOT / ".local/bin/dotfiles-update")))
update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update)


class UpdateTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.seed = self.root / "seed"
        self.repo = self.root / "repo"
        self.state = self.home / ".local/state/dotfiles"
        self.marker = self.home / "installs"
        self.env = patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_STATE_HOME": str(self.home / ".local/state"),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Test", "GIT_COMMITTER_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.seed.mkdir()
        self.git(self.seed, "init", "-q", "-b", "main")
        (self.seed / ".config").mkdir()
        (self.seed / ".config/example").write_text("initial\n")
        (self.seed / "README.md").write_text("documentation\n")
        (self.seed / "install.sh").write_text(
            '#!/bin/sh\necho install >> "$HOME/installs"\n'
            'printf "%s\\n" "$*" > "$HOME/last-install-args"\n'
            'if [ -e "$HOME/fail-install" ]; then echo INSTALL_FAILED >&2; exit 1; fi\n')
        self.commit()
        self.git(self.root, "clone", "-q", str(self.seed), str(self.repo))
        self.enterContext(patch.object(update, "ROOT", self.repo))
        self.enterContext(patch.object(update, "COOLDOWN", 0))

    def git(self, repo, *args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              text=True, capture_output=True).stdout.strip()

    def commit(self):
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-qm", "fixture")

    def run_update(self, *args):
        with patch.object(sys, "argv", ["dotfiles-update", *args]):
            return update.main()

    def change(self, name, text):
        (self.seed / name).write_text(text)
        self.commit()

    def test_unchanged_and_documentation_only_updates_do_not_install(self):
        self.assertEqual(self.run_update(), 0)
        self.change("README.md", "new documentation\n")
        self.assertEqual(self.run_update(), 0)
        self.assertFalse(self.marker.exists())
        self.assertEqual((self.repo / "README.md").read_text(), "new documentation\n")

    def test_changed_inputs_apply_once_and_local_overlay_changes_apply(self):
        self.assertEqual(self.run_update(), 0)
        self.change(".config/example", "new setting\n")
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(self.marker.read_text().splitlines(), ["install"])
        self.assertEqual((self.home / "last-install-args").read_text(), "--background\n")
        self.change(".gitignore", "UNIVERSAL_AGENT_DIRECTIVES.local.md\n")
        self.assertEqual(self.run_update(), 0)
        (self.repo / "UNIVERSAL_AGENT_DIRECTIVES.local.md").write_text("local instructions\n")
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(len(self.marker.read_text().splitlines()), 2)

    def test_failed_install_is_logged_and_retried_without_another_pull_change(self):
        self.assertEqual(self.run_update(), 0)
        receipt = (self.state / "applied-inputs").read_text()
        self.change(".config/example", "new setting\n")
        failure = self.home / "fail-install"
        failure.touch()
        self.assertEqual(self.run_update(), 1)
        self.assertEqual((self.state / "applied-inputs").read_text(), receipt)
        log = (self.state / "last-error.log").read_text()
        self.assertIn("INSTALL_FAILED", log)
        failure.unlink()
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(len(self.marker.read_text().splitlines()), 2)
        self.assertEqual((self.state / "last-error.log").read_text(), log)

    def test_dirty_branch_and_wrong_upstream_are_not_advanced(self):
        original = self.git(self.repo, "rev-parse", "HEAD")
        self.change(".config/example", "new setting\n")
        (self.repo / ".config/example").write_text("local edit\n")
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), original)
        self.git(self.repo, "restore", ".config/example")
        self.git(self.repo, "checkout", "-qb", "work")
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), original)
        self.git(self.repo, "checkout", "-q", "main")
        self.git(self.repo, "remote", "rename", "origin", "elsewhere")
        self.assertEqual(self.run_update(), 0)
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), original)
        self.assertFalse(self.marker.exists())

    def test_foreground_install_and_background_update_share_lock(self):
        self.state.mkdir(parents=True)
        with (self.state / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.run_update(), 0)
            self.assertEqual(self.run_update("--install"), 1)
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.state / "last-attempt").exists())

    def test_cooldown_stops_subprocesses(self):
        self.assertEqual(self.run_update(), 0)
        with patch.object(update, "COOLDOWN", 300), patch.object(update.Runner, "run") as run:
            self.assertEqual(self.run_update(), 0)
            run.assert_not_called()

    def test_timeout_kills_descendants_and_releases_lock(self):
        def hang(runner, applied):
            runner.run(["sh", "-c", '(sleep 1; echo leaked > "$HOME/leaked") & wait'])
        with patch.object(update, "TIMEOUT", 0.2), patch.object(update, "update", side_effect=hang):
            self.assertEqual(self.run_update(), 1)
        self.assertIn("timed out", (self.state / "last-error.log").read_text())
        time.sleep(1.1)
        self.assertFalse((self.home / "leaked").exists())
        with (self.state / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == "__main__":
    unittest.main()
