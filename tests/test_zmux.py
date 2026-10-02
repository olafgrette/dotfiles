"""Check startup/recovery; opt in to real Zellij with ZMUX_INTEGRATION=1."""

import json
import os
from pathlib import Path
import shutil
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
    if os.environ.get('TEST_TRANSIENT') == '1':
        if Path(os.environ['TEST_STATE'] + '-deleted').exists():
            if Path(os.environ['TEST_STATE'] + '-fresh').exists():
                print('review-session [Created now]')
        else:
            suffix = '' if queries == 2 and os.environ.get('TEST_BRIEF', '1') == '1' else ' (EXITED - attach to resurrect)'
            print('review-session [Created now]' + suffix)
    elif queries >= int(os.environ['TEST_READY']):
        print('review-session [Created now]')
elif '--create-background' in args:
    if Path(os.environ['TEST_STATE'] + '-deleted').exists():
        if os.environ.get('TEST_FRESH') == 'failed':
            print('fresh creation failed', file=sys.stderr)
            sys.exit(1)
        Path(os.environ['TEST_STATE'] + '-fresh').touch()
        sys.exit(0)
    if os.environ['TEST_CREATE'] != '0':
        print('creation failed', file=sys.stderr)
    sys.exit(int(os.environ['TEST_CREATE']))
elif args[0] == 'delete-session':
    if os.environ.get('TEST_DELETE') == 'failed':
        print('deletion failed', file=sys.stderr)
        sys.exit(1)
    Path(os.environ['TEST_STATE'] + '-deleted').touch()
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

    def test_failed_start_without_saved_session_reports_original_error(self):
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

    def test_briefly_running_resurrection_is_cleared_and_retried(self):
        result, log = self.run_zmux(TEST_MANAGER="1", TEST_TRANSIENT="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("clearing failed saved session", result.stderr)
        commands = log.splitlines()
        self.assertEqual(commands.count("zellij delete-session review-session"), 1)
        self.assertEqual(commands.count("zellij attach --create-background review-session"), 2)
        self.assertEqual(commands[-1], "zellij attach --create review-session")
        self.assertNotIn("--force", log)
        self.assertNotIn("-recovery", log)

    def test_saved_session_that_never_starts_is_cleared(self):
        result, log = self.run_zmux(TEST_MANAGER="1", TEST_TRANSIENT="1", TEST_BRIEF="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log.count("zellij delete-session review-session"), 1)
        self.assertIn("zellij attach --create review-session", log.splitlines())

    def test_failed_fresh_start_stops_after_one_reset(self):
        result, log = self.run_zmux(TEST_MANAGER="1", TEST_TRANSIENT="1", TEST_FRESH="failed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not start fresh session", result.stderr)
        self.assertNotIn("zellij attach --create ", log)
        self.assertEqual(log.count("zellij delete-session review-session"), 1)
        self.assertLess(log.count("list-sessions"), 100)

    def test_failed_deletion_stops_without_force_or_fresh_start(self):
        result, log = self.run_zmux(TEST_MANAGER="1", TEST_TRANSIENT="1", TEST_DELETE="failed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("deletion failed", result.stderr)
        self.assertEqual(log.count("zellij attach --create-background review-session"), 1)
        self.assertNotIn("zellij attach --create ", log)
        self.assertNotIn("--force", log)


@unittest.skipUnless(os.environ.get("ZMUX_INTEGRATION") == "1", "set ZMUX_INTEGRATION=1 for real Zellij")
class ZmuxIntegrationTest(unittest.TestCase):
    def test_plugin_only_saved_layout_recovers_with_a_real_terminal(self):
        real_zellij = shutil.which("zellij")
        self.assertIsNotNone(real_zellij, "integration check requires Zellij")
        with tempfile.TemporaryDirectory(prefix="zmux-") as temporary:
            root = Path(temporary)
            # Isolate config, cache, sockets, logs, and pane shells from the user.
            env = {key: value for key, value in os.environ.items() if not key.startswith("ZELLIJ")}
            env.update(HOME=str(root), XDG_CONFIG_HOME=str(root / "config"),
                       XDG_CACHE_HOME=str(root / "cache"), XDG_DATA_HOME=str(root / "data"),
                       XDG_STATE_HOME=str(root / "state"), XDG_RUNTIME_DIR=str(root / "run"),
                       ZELLIJ_SOCKET_DIR=str(root / "sockets"), TMPDIR=str(root), SHELL="/bin/sh",
                       ZELLIJ_CONFIG_FILE=str(root / "config" / "zellij" / "config.kdl"))
            (root / "run").mkdir(mode=0o700)
            config = Path(env["ZELLIJ_CONFIG_FILE"])
            config.parent.mkdir(parents=True)
            config.write_text('default_shell "/bin/sh"\nshow_startup_tips false\nshow_release_notes false\n')

            def zellij(*args, check=True):
                return subprocess.run([real_zellij, *args], env=env, text=True,
                                      capture_output=True, timeout=10, check=check)

            setup = zellij("setup", "--check").stdout
            cache = Path(next(line.removeprefix("[CACHE DIR]: ") for line in setup.splitlines()
                              if line.startswith("[CACHE DIR]: ")))
            self.assertTrue(cache.is_relative_to(root), setup)
            # This fixture targets the cache contract shipped in Zellij 0.45.
            session = "zmux-integration"
            saved = cache / "contract_version_1" / "session_info" / session
            saved.mkdir(parents=True)
            layout = '''layout {
    tab name="1" hide_floating_panes=true {
        pane size=1 borderless=true {
            plugin location="zellij:tab-bar"
        }
        pane borderless=true {
            plugin location="zellij:status-bar"
        }
    }
    tab name="3" hide_floating_panes=true {
        pane size=1 borderless=true {
            plugin location="zellij:tab-bar"
        }
        pane borderless=true {
            plugin location="zellij:status-bar"
        }
    }
}
'''
            (saved / "session-layout.kdl").write_text(layout)
            (saved / "pane_1").write_text("retained scrollback\n")
            self.assertIn(session, zellij("list-sessions", "--no-formatting").stdout)

            bin_dir = root / "bin"
            bin_dir.mkdir()
            # Run real startup/resurrection. Replace only the foreground UI with
            # a pane query, which must reach the server selected by the wrapper.
            scripts = {
                "systemctl": "#!/bin/sh\nexit 1\n",
                "pgrep": "#!/bin/sh\nexit 1\n",
                "zellij": f'''#!/usr/bin/env python3
import os
import sys
args = sys.argv[1:]
with open({str(root / "commands")!r}, 'a') as log:
    log.write(repr(args) + '\\n')
if args[:2] == ['attach', '--create']:
    args = ['--session', args[2], 'action', 'list-panes', '--json']
os.execv({real_zellij!r}, [{real_zellij!r}, *args])
''',
            }
            for name, contents in scripts.items():
                script = bin_dir / name
                script.write_text(contents)
                script.chmod(0o755)
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            try:
                result = subprocess.run([
                    "fish", "--no-config", "-c", "source $argv[1]; zmux $argv[2]",
                    str(ROOT / ".config/fish/functions/zmux.fish"), session,
                ], env=env, text=True, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                logs = {str(path.relative_to(root)): path.read_text()[-10000:]
                        for path in root.rglob("zellij.log")}
                self.assertIn(f"clearing failed saved session '{session}'", result.stderr,
                              f"commands={(root / 'commands').read_text()}; stdout={result.stdout}; logs={logs}")
                self.assertTrue(any("0 tiled + 0 floating panes created" in log for log in logs.values()), logs)
                panes = json.loads(result.stdout)
                self.assertTrue(any(not pane["is_plugin"] and not pane["exited"] for pane in panes), panes)
                self.assertFalse((saved / "pane_1").exists())
                self.assertIn(f"['attach', '--create', '{session}']", (root / "commands").read_text())
            except subprocess.TimeoutExpired as error:
                logs = {str(path.relative_to(root)): path.read_text()[-6000:]
                        for path in root.rglob("zellij.log")}
                self.fail(f"{error}; stdout={error.stdout!r}; stderr={error.stderr!r}; logs={logs}")
            finally:
                # Only these test sessions, in the isolated socket directory.
                zellij("kill-session", session, check=False)


if __name__ == "__main__":
    unittest.main()
