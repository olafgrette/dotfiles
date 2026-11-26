"""Run the installer only in temporary HOME/repository copies with setup stubs."""

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile
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
        tracked = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, check=True,
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
        archive = self.root / "starship.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            content = b"#!/bin/sh\nexit 0\n"
            member = tarfile.TarInfo("starship")
            member.size = len(content)
            tar.addfile(member, io.BytesIO(content))
        cursor_archive = self.root / "cursors.tar.gz"
        with tarfile.open(cursor_archive, "w:gz") as tar:
            for name, content in (("broodwar/index.theme", b"[Icon Theme]\nName=broodwar\n"),
                                  ("broodwar/cursors/left_ptr", b"Xcur fixture")):
                member = tarfile.TarInfo(name)
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
        manifest = self.repo / "dots-sh/artifacts.json"
        data = json.loads(manifest.read_text())
        for entry in data["files"].values():
            content = archive.read_bytes() if entry["path"].endswith(".tar.gz") else b"fixture\n"
            if entry["path"].endswith("broodwar_linux_cursor.tar.gz"):
                content = cursor_archive.read_bytes()
            entry["sha256"] = hashlib.sha256(content).hexdigest()
        manifest.write_text(json.dumps(data))
        self.stub("curl", '''echo "curl $*" >> "$SETUP_LOG"
args="$*"
while [ "$1" != -o ]; do shift; done
case "$args" in
    *broodwar_linux_cursor.tar.gz) cat "$CURSOR_FIXTURE" > "$2" ;;
    *.tar.gz) cat "$STARSHIP_FIXTURE" > "$2" ;;
    *) printf 'fixture\\n' > "$2" ;;
esac''')
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin),
                        XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / ".local/share"),
                        XDG_CACHE_HOME=str(self.home / ".cache"),
                        XDG_STATE_HOME=str(self.home / ".local/state"),
                        DISPLAY=":fixture", SETUP_LOG=str(self.root / "setup.log"),
                        STARSHIP_FIXTURE=str(archive), CURSOR_FIXTURE=str(cursor_archive))
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
        local_skill = self.home / ".gemini/config/skills/local-only"
        local_skill.mkdir(parents=True)
        (local_skill / "SKILL.md").write_text("---\nname: local-only\n---\n")
        self.install("--background")
        self.install("--background")
        self.assertTrue((self.home / ".config/fish").is_symlink())
        self.assertTrue((self.home / ".codex/AGENTS.md").is_file())
        for root in (".claude/skills", ".codex/skills", ".gemini/config/skills"):
            target = self.home / root / "investigation"
            self.assertTrue(target.is_symlink())
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertFalse((target / "investigation").exists())
        self.assertTrue((local_skill / "SKILL.md").is_file())
        self.assertFalse((self.root / "setup.log").exists())

    def test_directive_read_failures_preserve_all_installed_files(self):
        self.install("--background")
        targets = [self.home / name for name in (
            ".claude/CLAUDE.md", ".codex/AGENTS.md", ".gemini/GEMINI.md", ".opencode/AGENTS.md",
        )]
        before = [path.read_bytes() for path in targets]
        source = self.repo / "UNIVERSAL_AGENT_DIRECTIVES.md"
        original = source.read_bytes()
        source.unlink()
        for failure in ("shared", "local"):
            with self.subTest(failure=failure):
                if failure == "local":
                    source.write_bytes(original)
                    (self.repo / "UNIVERSAL_AGENT_DIRECTIVES.local.md").symlink_to("missing")
                result = subprocess.run(["bash", str(self.repo / "install.sh"), "--background"],
                                        env=self.env, text=True, capture_output=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual([path.read_bytes() for path in targets], before)

    def test_directive_replacement_preserves_old_file_on_failure_and_skips_equal_content(self):
        self.install("--background")
        target = self.home / ".claude/CLAUDE.md"
        before = target.read_bytes()
        inode = target.stat().st_ino
        self.install("--background")
        self.assertEqual(target.stat().st_ino, inode)
        (self.repo / "UNIVERSAL_AGENT_DIRECTIVES.local.md").write_text("Local fixture\n")
        (self.bin / "mv").unlink()
        self.stub("mv", 'echo "fixture: replacement failed" >&2; exit 1')
        result = subprocess.run(["bash", str(self.repo / "install.sh"), "--background"],
                                env=self.env, text=True, capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("replacement failed", result.stderr)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(list(target.parent.glob("CLAUDE.md.*")), [])

    def test_skill_cleanup_only_removes_broken_repository_links(self):
        for directory in (".claude/skills", ".codex/skills", ".gemini/config/skills"):
            destination = self.home / directory
            destination.mkdir(parents=True)
            (destination / "removed").symlink_to(str(self.repo.resolve() / "skills/removed") + "/")
            (destination / "local-broken").symlink_to(self.root / "private/missing")
            (destination / "relative-broken").symlink_to("../missing")
            (destination / "similar-prefix").symlink_to(self.repo.resolve() / "skills-other/missing")
            (destination / "local-directory").mkdir()
        self.install("--background")
        for directory in (".claude/skills", ".codex/skills", ".gemini/config/skills"):
            destination = self.home / directory
            self.assertFalse((destination / "removed").is_symlink())
            for name in ("local-broken", "relative-broken", "similar-prefix"):
                self.assertTrue((destination / name).is_symlink())
            self.assertTrue((destination / "local-directory").is_dir())
            self.assertTrue((destination / "investigation/SKILL.md").is_file())

    def test_default_retains_network_setup_and_linger(self):
        self.install()
        log = (self.root / "setup.log").read_text()
        self.assertIn("loginctl enable-linger", log)
        self.assertIn("dots.oag.sh/assets/starship/", log)
        self.assertTrue(os.access(self.home / ".local/bin/starship", os.X_OK))
        self.assertIn("cursor_frozen.glsl", log)
        self.assertIn("zellij-choose-tree.wasm", log)
        self.assertIn("dots.oag.sh/assets/broodwar-cursors/", log)
        self.assertTrue((self.home / ".local/share/icons/broodwar/index.theme").is_file())

    def test_cursor_install_honors_xdg_data_home(self):
        self.env["XDG_DATA_HOME"] = str(self.root / "data")
        self.install()
        self.assertTrue((self.root / "data/icons/broodwar/index.theme").is_file())
        self.assertFalse((self.home / ".local/share/icons/broodwar").exists())

    def test_cursor_install_skips_headless_and_macos(self):
        for system, display in (("Linux", ""), ("Darwin", ":fixture")):
            with self.subTest(system=system):
                self.stub("uname", f'case "$1" in -n) echo unknown-test-host ;; *) echo {system} ;; esac')
                self.env["DISPLAY"] = display
                self.env.pop("WAYLAND_DISPLAY", None)
                self.install()
                self.assertNotIn("broodwar", (self.root / "setup.log").read_text())
                self.assertFalse((self.home / ".local/share/icons/broodwar").exists())

    def test_verified_downloads_are_reused_and_corruption_is_repaired(self):
        self.install()
        self.env["PATH"] += os.pathsep + str(self.home / ".local/bin")
        (self.root / "setup.log").unlink()
        self.install()
        self.assertNotIn("curl ", (self.root / "setup.log").read_text())
        shader = self.home / ".config/ghostty/shaders/cursor_frozen.glsl"
        shader.write_text("corrupt")
        self.install()
        self.assertEqual(shader.read_text(), "fixture\n")

    def test_dms_plugin_restore_runs_only_in_foreground(self):
        config = self.home / ".config/dms"
        config.mkdir(parents=True)
        (config / ".firstlaunch").touch()
        shared = self.repo / ".config/dms/plugins.lock.json"
        shared.write_text('{"lockfileVersion": 1, "plugins": {}}\n')
        self.stub("dms", 'echo "dms $*" >> "$SETUP_LOG"')
        self.install()
        log = (self.root / "setup.log").read_text()
        self.assertIn("dms plugins restore ", log)
        self.assertNotIn("--prune", log)
        (self.root / "setup.log").unlink()
        self.install("--background")
        self.assertFalse((self.root / "setup.log").exists())
        self.assertTrue((config / "config.d/10-dotfiles.json").is_file())
        self.assertFalse((self.home / ".config/DankMaterialShell").exists())

    def test_background_refuses_first_native_migration_without_changing_settings(self):
        config = self.home / ".config/dms"
        config.mkdir(parents=True)
        (config / ".firstlaunch").touch()
        settings = '{"existingPreference": true}\n'
        (config / "settings.json").write_text(settings)
        result = subprocess.run(["bash", str(self.repo / "install.sh"), "--background"],
                                env=self.env, text=True, capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("foreground migration", result.stderr)
        self.assertEqual((config / "settings.json").read_text(), settings)
        self.assertFalse((config / "config.d").exists())

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
