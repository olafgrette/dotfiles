"""Black-box tests for init.sh — trimmed, harness deduplicated."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

from tests._helpers import run_pty

ROOT = Path(__file__).parents[1]
INIT = ROOT / "init.sh"


def write_executable(path, body):
    path.write_text(body)
    path.chmod(0o755)


def fake_init(tmp, distro="arch"):
    release = Path(tmp) / "os-release"
    release.write_text(f"ID={distro}\n")
    script = Path(tmp) / "init.sh"
    text = INIT.read_text().replace("OS_RELEASE=/etc/os-release", f"OS_RELEASE={shlex.quote(str(release))}", 1)
    script.write_text(text)
    script.chmod(0o755)
    return script


def fake_repo(path, *, personal=("testhost",), hypr_home=None):
    path.mkdir(parents=True)
    (path / "personal-hosts").write_text("\n".join(personal) + "\n")
    write_executable(path / "aconf.sh", r'''#!/bin/sh
if [ "${ACONF_PROMPT:-0}" = 1 ]; then
    printf 'aconf confirmation [y/N] ' >&2
    IFS= read -r reply || { echo 'aconf confirmation input closed' >&2; exit 3; }
    [ "$reply" = y ] || { echo 'aconf confirmation refused' >&2; exit 2; }
fi
printf 'aconf %s\n' "$*" >> "$COMMAND_LOG"
''')
    write_executable(path / "install.sh", '#!/bin/sh\nprintf \'install %s\\n\' "$*" >> "$COMMAND_LOG"\n')
    write_executable(path / "readiness.sh", "#!/bin/sh\nexit 0\n")
    if hypr_home is not None:
        (hypr_home / ".config/hypr").mkdir(parents=True)
    return path


def stub_env(tmp, *, host="testhost", uid=1000, git_present=True, dms_present=True, dms_exit=0, dms_creates_hypr=True):
    tmp = Path(tmp)
    bindir = tmp / "bin"
    bindir.mkdir()
    home = tmp / "home"
    home.mkdir()
    origin = fake_repo(tmp / "origin", personal=(host,))
    command_log = tmp / "commands.log"
    for name in (
        "awk", "bash", "cat", "curl", "dirname", "fish", "grep", "jq",
        "uname", "hostname", "id", "mktemp", "rm", "mkdir",
    ):
        real = shutil.which(name)
        if real:
            (bindir / name).symlink_to(real)
    for p in (bindir / "hostname", bindir / "id"):
        if p.is_symlink() or p.exists():
            p.unlink()
    (bindir / "hostname").write_text(f"#!/bin/sh\necho {host}\n")
    (bindir / "hostname").chmod(0o755)
    (bindir / "id").write_text(f"#!/bin/sh\necho {uid}\n")
    (bindir / "id").chmod(0o755)
    (bindir / "git").write_text("#!/bin/sh\nif [ \"$1\" = clone ]; then mkdir -p \"$3\"; echo cloned > \"$3/README\"; fi\nprintf 'git %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n")
    (bindir / "git").chmod(0o755)
    if not git_present:
        (bindir / "git").write_text("#!/bin/sh\nexit 127\n")
        (bindir / "git").chmod(0o755)
    dms_creates = "1" if dms_creates_hypr else "0"
    (bindir / "dms").write_text(
        f"#!/bin/sh\nprintf 'dms %s\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
        f"if [ ! \"{dms_present}\" = True ]; then exit 127; fi\n"
        f"if [ \"$*\" = \"setup\" ] && [ \"{dms_creates}\" = \"1\" ]; then mkdir -p \"$HOME/.config/hypr\"; fi\n"
        f"exit {dms_exit}\n"
    )
    (bindir / "dms").chmod(0o755)
    env = {**os.environ, "PATH": str(bindir), "HOME": str(home), "COMMAND_LOG": str(command_log)}
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env, home, command_log


def log_lines(log):
    return log.read_text().splitlines() if log.exists() else []


class InitTest(unittest.TestCase):
    def test_root_is_refused_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, _, _ = stub_env(tmp, uid=0)
            result = run_pty(["bash", str(script)], env=env, input_text="")
            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing to run as root", result.stdout.lower())

    def test_default_hostname_is_refused_with_remediation(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, _, _ = stub_env(tmp, host="archlinux")
            result = run_pty(["bash", str(script)], env=env, input_text="")
            self.assertEqual(result.returncode, 2)
            self.assertIn("archlinux", result.stdout)
            self.assertIn("hostnamectl", result.stdout)

    def test_piped_script_without_controlling_terminal_refuses_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env = {**os.environ, "PATH": os.environ["PATH"], "HOME": str(Path(tmp) / "home")}
            result = subprocess.run(["sh", str(script)], capture_output=True, text=True, env=env, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertIn("controlling terminal", result.stderr.lower())

    def test_repo_ghostty_link_refuses_dms_and_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, home, log = stub_env(tmp)
            repo = fake_repo(home / "dotfiles", personal=("testhost",))
            (repo / ".config/ghostty").mkdir(parents=True)
            ghostty_link = home / ".config/ghostty"
            ghostty_link.parent.mkdir(parents=True, exist_ok=True)
            ghostty_link.symlink_to(repo / ".config/ghostty")
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("Ghostty is linked", result.stdout)
            self.assertFalse(any(line.startswith("dms ") for line in log_lines(log)))
            self.assertFalse(any(line.startswith("install ") for line in log_lines(log)))

    def test_failed_dms_stops_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, home, log = stub_env(tmp, dms_exit=1)
            fake_repo(home / "dotfiles", personal=("testhost",))
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("dms setup failed", result.stdout.lower())
            self.assertFalse(any(line.startswith("install ") for line in log_lines(log)))

    def test_missing_dms_stops_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, home, log = stub_env(tmp, dms_present=False)
            fake_repo(home / "dotfiles", personal=("testhost",))
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("dms", result.stdout.lower())
            self.assertFalse(any(line.startswith("install ") for line in log_lines(log)))

    def test_missing_home_layer_prerequisite_stops_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp, distro="fedora")
            env, home, log = stub_env(tmp)
            fake_repo(home / "dotfiles", personal=("testhost",))
            (Path(env["PATH"]) / "jq").unlink()
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("missing prerequisites: jq", result.stdout)
            self.assertFalse(any(line.startswith("install ") for line in log_lines(log)))

    def test_dms_without_hypr_output_stops_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, home, log = stub_env(tmp, dms_creates_hypr=False)
            fake_repo(home / "dotfiles", personal=("testhost",))
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("Hyprland configuration", result.stdout)
            self.assertFalse(any(line.startswith("install ") for line in log_lines(log)))

    def test_personal_arch_runs_dms_then_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, home, log = stub_env(tmp)
            fake_repo(home / "dotfiles", personal=("testhost",))
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 0, result.stdout)
            lines = log_lines(log)
            self.assertTrue(any(line.startswith("aconf ") for line in lines))
            self.assertTrue(any(line.startswith("dms setup") for line in lines))
            self.assertTrue(any(line.startswith("install ") for line in lines))
            # ordering: aconf before dms before install
            aconf_idx = next(i for i, l in enumerate(lines) if l.startswith("aconf "))
            dms_idx = next(i for i, l in enumerate(lines) if l.startswith("dms "))
            install_idx = next(i for i, l in enumerate(lines) if l.startswith("install "))
            self.assertLess(aconf_idx, dms_idx)
            self.assertLess(dms_idx, install_idx)

    def test_ready_personal_arch_applies_then_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, home, log = stub_env(tmp)
            fake_repo(home / "dotfiles", personal=("testhost",))
            (home / ".config/hypr").mkdir(parents=True)
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 0, result.stdout)
            lines = log_lines(log)
            self.assertTrue(any(line.startswith("aconf ") for line in lines))
            self.assertFalse(any(line.startswith("dms ") for line in lines))
            self.assertTrue(any(line.startswith("install ") for line in lines))

    def test_non_arch_clones_and_installs_without_system_or_dms_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp, distro="fedora")
            env, home, log = stub_env(tmp)
            fake_repo(home / "dotfiles", personal=("testhost",))
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 0, result.stdout)
            lines = log_lines(log)
            self.assertFalse(any(line.startswith("aconf ") for line in lines))
            self.assertFalse(any(line.startswith("dms ") for line in lines))
            self.assertTrue(any(line.startswith("install ") for line in lines))

    def test_undeclared_arch_runs_install_without_aur_or_dms_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = fake_init(tmp)
            env, home, log = stub_env(tmp, host="unknownhost")
            fake_repo(home / "dotfiles", personal=("testhost",))
            result = run_pty(["bash", str(script)], env=env)
            self.assertEqual(result.returncode, 0, result.stdout)
            lines = log_lines(log)
            self.assertFalse(any(line.startswith("aconf ") for line in lines))
            self.assertFalse(any(line.startswith("dms ") for line in lines))
            self.assertTrue(any(line.startswith("install ") for line in lines))


if __name__ == "__main__":
    unittest.main()
