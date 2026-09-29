"""Check session preservation and startup fallback without launching Zellij."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class ZmuxTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / "commands"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, HOME=str(self.root), PATH=f"{self.bin}:{os.environ['PATH']}",
                        TEST_LOG=str(self.log), TEST_STATE=str(self.root / "queries"),
                        TEST_MANAGER="0", TEST_SCOPE="0", TEST_READY="4", TEST_CREATE="0")
        self.env.pop("ZELLIJ", None)
        self.stub("systemctl", 'echo systemctl >> "$TEST_LOG"\nexit "$TEST_MANAGER"')
        self.stub("systemd-run", 'echo scoped-start >> "$TEST_LOG"\nexit "$TEST_SCOPE"')
        self.stub("pgrep", "exit 1")
        self.stub("sleep", "exit 0")
        zellij = self.bin / "zellij"
        zellij.write_text('''#!/usr/bin/env python3
import os
from pathlib import Path
import sys
args = sys.argv[1:]
with open(os.environ['TEST_LOG'], 'a') as log:
    log.write('zellij ' + ' '.join(args) + '\\n')
if args[0] == 'list-sessions':
    state = Path(os.environ['TEST_STATE'])
    queries = int(state.read_text()) + 1 if state.exists() else 1
    state.write_text(str(queries))
    if queries >= int(os.environ['TEST_READY']):
        print('review-session [Created now]')
elif '--create-background' in args:
    if os.environ['TEST_CREATE'] != '0':
        print('creation failed', file=sys.stderr)
    sys.exit(int(os.environ['TEST_CREATE']))
''')
        zellij.chmod(0o755)

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def run_zmux(self, **env):
        result = subprocess.run([
            "fish", "--no-config", "-c", 'source $argv[1]; zmux review-session',
            str(ROOT / ".config/fish/functions/zmux.fish"),
        ], env={**self.env, **env}, text=True, capture_output=True, timeout=10)
        return result, self.log.read_text()

    def test_unavailable_manager_uses_direct_creation(self):
        result, log = self.run_zmux(TEST_MANAGER="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("scoped-start", log)
        self.assertIn("zellij attach --create-background review-session", log)
        self.assertIn("zellij attach --create review-session", log)
        self.assertNotIn("delete-session", log)

    def test_failed_scope_falls_back_and_waits_for_delayed_readiness(self):
        result, log = self.run_zmux(TEST_SCOPE="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scoped-start", log)
        self.assertIn("zellij attach --create-background review-session", log)
        self.assertIn("zellij attach --create review-session", log)

    def test_successful_scope_does_not_start_directly(self):
        result, log = self.run_zmux()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scoped-start", log)
        self.assertNotIn("zellij attach --create-background", log)
        self.assertIn("zellij attach --create review-session", log)

    def test_failed_start_preserves_saved_session_and_reports_original_error(self):
        result, log = self.run_zmux(TEST_MANAGER="1", TEST_CREATE="1", TEST_READY="1000")
        self.assertEqual(result.returncode, 1)
        self.assertIn("creation failed", result.stderr)
        self.assertIn("saved session retained", result.stderr)
        self.assertNotIn("delete-session", log)
        self.assertNotIn("zellij attach --create review-session", log)
        self.assertLess(log.count("list-sessions"), 100)

    def test_existing_session_does_not_attempt_creation(self):
        result, log = self.run_zmux(TEST_READY="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("systemctl", log)
        self.assertNotIn("create-background", log)


if __name__ == "__main__":
    unittest.main()
