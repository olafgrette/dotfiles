"""Exercise Fish's real startup order in a temporary configuration directory."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).parents[1]


class FishStartupTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = self.root / ".config/fish"
        (self.config / "conf.d").mkdir(parents=True)
        (self.config / "functions").mkdir()
        for name in ("config.fish", "conf.d/00-local-override.fish"):
            shutil.copy2(ROOT / ".config/fish" / name, self.config / name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("hx", "starship"):
            path = self.bin / name
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o755)
        self.local_bin = self.root / "local-bin"
        self.local_bin.mkdir()
        self.loads = self.root / "local-loads"
        self.background = self.root / "background-env"
        (self.config / "functions/background-startup.fish").write_text('''function background-startup
    printf '%s|%s|%s\\n' $EDITOR $npm_config_prefix $PATH[1] > $TEST_BACKGROUND
end
''')
        self.env = dict(os.environ, HOME=str(self.root), PATH=f"{self.bin}:{os.environ['PATH']}",
                        XDG_CONFIG_HOME=str(self.root / ".config"),
                        XDG_DATA_HOME=str(self.root / ".local/share"),
                        XDG_CACHE_HOME=str(self.root / ".cache"),
                        TEST_LOADS=str(self.loads), TEST_BACKGROUND=str(self.background),
                        TEST_LOCAL_BIN=str(self.local_bin))

    def local(self, name="local.fish"):
        path = self.config / name
        path.write_text('''set -gx EDITOR local-editor
set -gx npm_config_prefix /local-prefix
set -gx PATH $TEST_LOCAL_BIN $PATH
alias mux 'printf local-mux'
echo loaded >> $TEST_LOADS
''')
        path.chmod(0o600)
        return path

    def run_fish(self, interactive=False):
        command = ["fish"]
        if interactive:
            command.append("--interactive")
        command += ["-c", 'printf "%s|%s|" $EDITOR $npm_config_prefix; mux']
        return subprocess.run(command, env=self.env, text=True, capture_output=True, timeout=10)

    def test_local_values_and_alias_override_shared_defaults(self):
        self.local()
        result = self.run_fish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("local-editor|/local-prefix|local-mux", result.stdout)
        self.assertEqual(self.loads.read_text().splitlines(), ["loaded"])
        self.assertFalse(self.background.exists())

    def test_legacy_file_migrates_before_loading_and_runs_once(self):
        legacy = self.local("conf.d/local.fish")
        result = self.run_fish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("local-editor|/local-prefix|local-mux", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertFalse(legacy.exists())
        self.assertEqual((self.config / "local.fish").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.loads.read_text().splitlines(), ["loaded"])
        self.assertEqual(self.run_fish().returncode, 0)
        self.assertEqual(self.loads.read_text().splitlines(), ["loaded", "loaded"])

    def test_conflicting_override_files_are_preserved(self):
        legacy = self.config / "conf.d/local.fish"
        legacy.write_text("set -gx EDITOR legacy-editor\n")
        override = self.local()
        original = override.read_bytes()
        result = self.run_fish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Both files were preserved", result.stderr)
        self.assertIn("local-editor|/local-prefix|local-mux", result.stdout)
        self.assertEqual(override.read_bytes(), original)
        self.assertEqual(legacy.read_text(), "set -gx EDITOR legacy-editor\n")

    def test_relative_legacy_symlink_keeps_its_target(self):
        private = self.local("private.fish")
        legacy = self.config / "conf.d/local.fish"
        legacy.symlink_to("../private.fish")
        result = self.run_fish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("local-editor|/local-prefix|local-mux", result.stdout)
        self.assertEqual((self.config / "local.fish").resolve(), private)
        self.assertFalse(legacy.is_symlink())
        self.assertEqual(self.loads.read_text().splitlines(), ["loaded"])

    def test_background_child_inherits_final_local_environment(self):
        self.local()
        result = self.run_fish(interactive=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        deadline = time.monotonic() + 5
        while not self.background.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(self.background.read_text(), f"local-editor|/local-prefix|{self.local_bin}\n")
        self.assertEqual(self.loads.read_text().splitlines(), ["loaded"])

    def test_new_override_path_is_gitignored(self):
        result = subprocess.run(["git", "check-ignore", "-q", ".config/fish/local.fish"], cwd=ROOT)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
