"""Integration tests for the local-only files produced by secret-sync."""

import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
SECRET_SYNC = ROOT / ".config/fish/functions/secret-sync.fish"


class RcloneSecretSyncTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.staging = self.root / "staging"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.staging.mkdir()
        self.bin.mkdir()

        key = self.root / "source-key"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
            check=True,
        )
        self.ssh_item = self.root / "ssh.json"
        self.ssh_item.write_text(json.dumps({
            "type": 5,
            "sshKey": {
                "privateKey": key.read_text(),
                "publicKey": key.with_suffix(".pub").read_text(),
            },
        }))
        self.gdrive_item = self.root / "gdrive.json"
        self.gdrive_item.write_text(json.dumps({
            "login": {"username": "test-client", "password": "test-secret"},
        }))

        bw = self.bin / "bw"
        bw.write_text("""#!/bin/sh
case "$1" in
    sync) exit 0 ;;
    get)
        case "$3" in
            0bafc73b-*) exec cat "$TEST_SSH_ITEM" ;;
            *) exec cat "$TEST_GDRIVE_ITEM" ;;
        esac
        ;;
esac
exit 2
""")
        bw.chmod(0o755)

    def pull(self):
        env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "SECRET_SYNC_FUNCTION": str(SECRET_SYNC),
            "SECRET_SYNC_STAGING": str(self.staging),
            "TEST_SSH_ITEM": str(self.ssh_item),
            "TEST_GDRIVE_ITEM": str(self.gdrive_item),
        }
        env.pop("XDG_CONFIG_HOME", None)
        return subprocess.run(
            [
                "fish", "-c",
                "source $SECRET_SYNC_FUNCTION; __secret_sync_pull $SECRET_SYNC_STAGING 1",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def test_missing_config_is_seeded_from_bitwarden_client(self):
        result = self.pull()
        self.assertEqual(result.returncode, 0, result.stderr)
        config = self.home / ".config/rclone/rclone.conf"
        self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)
        self.assertEqual(
            config.read_text().splitlines(),
            [
                "[gdrive]",
                "type = drive",
                "scope = drive",
                "client_id = test-client",
                "client_secret = test-secret",
            ],
        )

    def test_existing_token_and_other_remote_are_preserved(self):
        config = self.home / ".config/rclone/rclone.conf"
        config.parent.mkdir(parents=True)
        config.write_text(
            "[other]\n"
            "type = local\n\n"
            "[gdrive]\n"
            "type = drive\n"
            "scope = drive\n"
            "client_id = old-client\n"
            "client_secret = old-secret\n"
            "token = {\"access_token\":\"test-token\"}\n"
        )

        result = self.pull()
        self.assertEqual(result.returncode, 0, result.stderr)
        contents = config.read_text()
        self.assertIn("[other]\ntype = local", contents)
        self.assertIn("client_id = test-client", contents)
        self.assertIn("client_secret = test-secret", contents)
        self.assertIn('token = {"access_token":"test-token"}', contents)
        self.assertNotIn("old-client", contents)
        self.assertNotIn("old-secret", contents)


if __name__ == "__main__":
    unittest.main()
