"""Artifact integrity and replacement behavior without network access."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import tarfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("artifacts", ROOT / "dots-sh/artifacts.py")
artifacts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artifacts)


class ArtifactsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / "plugin.wasm"
        self.entry = {"path": "assets/plugin/v1/plugin.wasm", "source": "https://upstream.example/plugin",
                      "sha256": hashlib.sha256(b"approved").hexdigest()}

    def download(self, content):
        def run(command, **kwargs):
            Path(command[command.index("-o") + 1]).write_bytes(content)
        return patch.object(artifacts.subprocess, "run", side_effect=run)

    def test_success_uses_mirror_and_reuses_verified_file(self):
        with self.download(b"approved") as run:
            artifacts.fetch(self.entry, self.destination)
            artifacts.fetch(self.entry, self.destination)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-1], artifacts.BASE + self.entry["path"])
        self.assertEqual(self.destination.read_bytes(), b"approved")

    def test_failed_integrity_preserves_previous_file_and_removes_partial(self):
        self.destination.write_bytes(b"old")
        with self.download(b"tampered"), self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            artifacts.fetch(self.entry, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"old")
        self.assertEqual(list(self.root.iterdir()), [self.destination])

    def test_ocs_resolution_is_only_used_for_upstream_downloads(self):
        entry = dict(self.entry, source_type="ocs")
        metadata = b'<ocs><meta><statuscode>100</statuscode></meta><data><content><downloadlink1>https://files.example/fresh-token</downloadlink1></content></data></ocs>'
        with patch.object(artifacts.subprocess, "check_output", return_value=metadata) as resolve:
            with self.download(b"approved") as run:
                artifacts.fetch(entry, self.destination, upstream=True)
            self.assertEqual(run.call_args.args[0][-1], "https://files.example/fresh-token")
            resolve.assert_called_once()
            resolve.reset_mock()
            with self.download(b"approved") as run:
                artifacts.fetch(entry, self.destination, force=True)
            resolve.assert_not_called()
            self.assertEqual(run.call_args.args[0][-1], artifacts.BASE + entry["path"])

    def test_ocs_rejects_missing_or_insecure_download(self):
        for metadata in (
            b'<ocs><meta><statuscode>101</statuscode></meta></ocs>',
            b'<ocs><meta><statuscode>100</statuscode></meta><data><content><downloadlink1>http://files.example/archive</downloadlink1></content></data></ocs>',
        ):
            with patch.object(artifacts.subprocess, "check_output", return_value=metadata):
                with self.assertRaisesRegex(ValueError, "HTTPS download"):
                    artifacts.source_url(dict(self.entry, source_type="ocs"))

    def test_interrupted_transfer_preserves_previous_file(self):
        self.destination.write_bytes(b"old")
        def interrupted(command, **kwargs):
            Path(command[command.index("-o") + 1]).write_bytes(b"partial")
            raise subprocess.CalledProcessError(28, command)
        with patch.object(artifacts.subprocess, "run", side_effect=interrupted):
            with self.assertRaises(subprocess.CalledProcessError):
                artifacts.fetch(self.entry, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"old")
        self.assertEqual(list(self.root.iterdir()), [self.destination])

    def test_stage_retains_unselected_versions_and_refuses_extra_files(self):
        (self.root / "init.sh").write_text("bootstrap")
        project = self.root / "dots-sh"
        project.mkdir()
        for name in ("_headers", "_redirects"):
            (project / name).write_text("rules")
        data = {"files": {"old": self.entry}, "current": {}}
        with patch.object(artifacts, "ROOT", project), self.download(b"approved"):
            artifacts.stage(data)
            self.assertTrue((project / "public" / self.entry["path"]).is_file())
            (project / "public/private.env").write_text("must not publish")
            with self.assertRaisesRegex(ValueError, "unexpected files"):
                artifacts.stage(data)

    def test_manifest_rejects_path_escape(self):
        entry = dict(self.entry, path="assets/../../private")
        (self.root / "artifacts.json").write_text(json.dumps({"files": {"bad": entry}, "current": {}}))
        with patch.object(artifacts, "ROOT", self.root), self.assertRaises(ValueError):
            artifacts.catalog()

    def test_stage_rejects_symlink_before_downloading(self):
        project = self.root / "dots-sh"
        project.mkdir()
        private = self.root / "private"
        private.mkdir()
        (project / "public").symlink_to(private)
        with patch.object(artifacts, "ROOT", project), self.download(b"approved") as run:
            with self.assertRaisesRegex(ValueError, "symlinks"):
                artifacts.stage({"files": {"old": self.entry}, "current": {}})
        run.assert_not_called()
        self.assertEqual(list(private.iterdir()), [])

    def test_supported_platform_selection(self):
        for system, machine, expected in (
            ("Linux", "x86_64", "x86_64-unknown-linux-musl"),
            ("Linux", "armv7l", "arm-unknown-linux-musleabihf"),
            ("Darwin", "arm64", "aarch64-apple-darwin"),
            ("Darwin", "x86_64", "x86_64-apple-darwin"),
        ):
            with self.subTest(system=system, machine=machine), \
                    patch.object(artifacts.platform, "system", return_value=system), \
                    patch.object(artifacts.platform, "machine", return_value=machine), \
                    patch.object(artifacts.sys, "maxsize", 2**63 - 1):
                self.assertEqual(artifacts.starship_target(), expected)
                self.assertIn("starship-" + expected, artifacts.catalog()["current"])

    def cursor_archive(self, extra=None):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as tar:
            for name, content in (("broodwar/index.theme", b"[Icon Theme]\nName=broodwar\n"),
                                  ("broodwar/cursors/left_ptr", b"Xcur fixture")):
                member = tarfile.TarInfo(name)
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
            link = tarfile.TarInfo("broodwar/cursors/default")
            link.type = tarfile.SYMTYPE
            link.linkname = "left_ptr"
            tar.addfile(link)
            if extra:
                tar.addfile(extra)
        content = output.getvalue()
        entry = dict(self.entry, sha256=hashlib.sha256(content).hexdigest())
        data = {"files": {"cursors": entry}, "current": {"broodwar-cursors": "cursors"}}
        return content, data

    def test_cursor_install_backs_up_existing_theme_and_is_idempotent(self):
        content, data = self.cursor_archive()
        destination = self.root / "icons/broodwar"
        destination.mkdir(parents=True)
        (destination / "custom").write_text("preserved")
        with self.download(content) as run:
            artifacts.install_cursors(data, destination)
            artifacts.install_cursors(data, destination)
        run.assert_called_once()
        self.assertEqual((destination.parent / "broodwar.bak/custom").read_text(), "preserved")
        self.assertTrue((destination / "index.theme").is_file())
        self.assertTrue((destination / "cursors/default").is_symlink())
        self.assertEqual((destination / "cursors/default").read_bytes(), b"Xcur fixture")

    def test_cursor_replacement_refuses_to_overwrite_backup(self):
        content, data = self.cursor_archive()
        destination = self.root / "broodwar"
        destination.mkdir()
        (self.root / "broodwar.bak").mkdir()
        with self.download(content) as run, self.assertRaisesRegex(ValueError, "backup already exists"):
            artifacts.install_cursors(data, destination)
        run.assert_not_called()

    def test_bad_cursor_archives_leave_existing_theme_intact(self):
        traversal = tarfile.TarInfo("broodwar/../../escape")
        link = tarfile.TarInfo("broodwar/cursors/escape")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../escape"
        for extra in (traversal, link):
            with self.subTest(name=extra.name):
                content, data = self.cursor_archive(extra)
                destination = self.root / "broodwar"
                destination.mkdir(exist_ok=True)
                (destination / "custom").write_text("preserved")
                with self.download(content), self.assertRaises(ValueError):
                    artifacts.install_cursors(data, destination)
                self.assertEqual((destination / "custom").read_text(), "preserved")
                self.assertFalse((self.root / "broodwar.bak").exists())
                self.assertFalse((self.root / "escape").exists())


if __name__ == "__main__":
    unittest.main()
