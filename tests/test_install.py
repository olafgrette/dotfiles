"""Run the installer only in temporary HOME/repository copies with setup stubs."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class InstallTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                                 capture_output=True, text=True).stdout.split("\0")
        for name in set(filter(None, tracked)) | {".local/bin/dotfiles-update"}:
            source = ROOT / name
            if not source.exists():
                continue  # Reflect tracked deletions before this change is committed.
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("awk", "bash", "basename", "cat", "chmod", "cmp", "dirname", "fish",
                     "grep", "id", "jq", "ln", "mkdir", "mktemp", "mv", "python3", "realpath",
                     "readlink", "rm", "sh", "touch"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.stub("hostname", "echo unknown-test-host")
        self.stub("uname", 'case "$1" in -n) echo unknown-test-host ;; *) echo Linux ;; esac')
        self.stub("loginctl", 'echo "loginctl $*" >> "$SETUP_LOG"\n'
                  'if [ "$1" = show-user ]; then echo no; fi')
        self.stub("curl", '''echo "curl $*" >> "$SETUP_LOG"
case "$*" in
    *starship.rs*) printf '#!/bin/sh\\nexit 0\\n' ;;
    *) while [ "$1" != -o ]; do shift; done; echo shader > "$2" ;;
esac''')
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin),
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / ".local/share"),
                        XDG_CACHE_HOME=str(self.home / ".cache"),
                        XDG_STATE_HOME=str(self.home / ".local/state"),
                        DISPLAY=":fixture", SETUP_LOG=str(self.root / "setup.log"))
        self.env.pop("DOTFILES_INSTALL_LOCKED", None)

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def install(self, *args):
        result = subprocess.run(["bash", str(self.repo / "install.sh"), *args], env=self.env,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_background_applies_files_without_network_or_linger(self):
        self.install("--background")
        self.assertTrue((self.home / ".config/fish").is_symlink())
        self.assertTrue((self.home / ".codex/AGENTS.md").is_file())
        self.assertTrue((self.home / ".codex/skills/investigation").is_symlink())
        self.assertFalse((self.root / "setup.log").exists())

    def test_default_retains_network_setup_and_linger(self):
        self.install()
        log = (self.root / "setup.log").read_text()
        self.assertIn("loginctl enable-linger", log)
        self.assertIn("starship.rs", log)
        self.assertIn("cursor_frozen.glsl", log)
        self.assertIn("zellij-choose-tree.wasm", log)

    def test_existing_library_directory_and_packages_remain_in_place(self):
        library = self.home / ".local/lib"
        package = library / "python/site-packages/example"
        package.mkdir(parents=True)
        (package / "data").write_text("local library\n")
        self.install("--background")
        self.install("--background")
        self.assertFalse(library.is_symlink())
        self.assertEqual((package / "data").read_text(), "local library\n")
        self.assertEqual((library / "llama-common.sh").resolve(), self.repo / ".local/lib/llama-common.sh")
        self.assertFalse((self.home / ".local/lib.bak").exists())

    def test_legacy_library_link_migrates_local_entries_without_touching_backup(self):
        library = self.home / ".local/lib"
        library.parent.mkdir()
        library.symlink_to(self.repo / ".local/lib")
        package = self.repo / ".local/lib/node_modules/example"
        package.mkdir(parents=True)
        (package / "data").write_text("installed package\n")
        (self.repo / ".local/lib/.local-state").write_text("hidden state\n")
        backup = self.home / ".local/lib.bak"
        backup.mkdir()
        (backup / "old-library").write_text("old backup\n")
        self.install("--background")
        self.install("--background")
        self.assertFalse(library.is_symlink())
        self.assertEqual((library / "node_modules/example/data").read_text(), "installed package\n")
        self.assertEqual((library / ".local-state").read_text(), "hidden state\n")
        self.assertFalse(package.exists())
        self.assertFalse((self.repo / ".local/lib/llama-common.sh").is_symlink())
        self.assertEqual((backup / "old-library").read_text(), "old backup\n")
        self.assertFalse((self.home / ".local/lib.dotfiles-link").exists())

    def test_library_migration_resumes_and_refuses_conflicting_local_entries(self):
        library = self.home / ".local/lib"
        library.mkdir(parents=True)
        recovery = self.home / ".local/lib.dotfiles-link"
        recovery.symlink_to(self.repo / ".local/lib")
        (library / "already-moved").write_text("preserved\n")
        source = self.repo / ".local/lib/pending"
        source.write_text("source\n")
        conflict = library / "pending"
        conflict.write_text("destination\n")
        result = subprocess.run(["bash", str(self.repo / "install.sh"), "--background"],
                                env=self.env, text=True, capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("both copies preserved", result.stderr)
        self.assertEqual(source.read_text(), "source\n")
        self.assertEqual(conflict.read_text(), "destination\n")
        self.assertTrue(recovery.is_symlink())
        conflict.rename(library / "resolved-conflict")
        self.install("--background")
        self.assertEqual((library / "already-moved").read_text(), "preserved\n")
        self.assertEqual((library / "pending").read_text(), "source\n")
        self.assertFalse(recovery.exists())


if __name__ == "__main__":
    unittest.main()
