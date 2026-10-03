"""Black-box tests for aconf.sh."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests._helpers import arch_only, run_pty

ROOT = Path(__file__).parents[1]
ACONF = ROOT / "aconf.sh"
ACONFMGR_CONFIG = ROOT / "aconfmgr"
BASE_PREREQUISITES = ("aconfmgr", "yay")
APPLY_PREREQUISITES = (
    "sudo", "timeshift", "date", "locale-gen", "systemctl", "curl", "mktemp",
    "rm", "pacman", "pacman-conf",
)
SUPPORT = ("bash", "cat", "dirname", "grep", "uname")


def fake_repo(tmp, *, personal=("testhost",), bypass_scope=True):
    repo = Path(tmp) / "dotfiles"
    repo.mkdir()
    shutil.copy(ACONF, repo / "aconf.sh")
    shutil.copytree(
        ACONFMGR_CONFIG, repo / "aconfmgr",
        ignore=shutil.ignore_patterns("aconfmgr.local", "99-unsorted.sh"),
    )
    (repo / "personal-hosts").write_text("\n".join(personal) + "\n")
    if bypass_scope:
        lines = [
            "short_host() { echo testhost; }",
            'require_declared_arch_host() { [ -d "$ACONFMGR_CONFIG" ]; }',
        ]
        (repo / "aconf.local.sh").write_text("\n".join(lines) + "\n")
    return repo


def stub_env(tmp, *, present=BASE_PREREQUISITES, host="testhost"):
    bindir = Path(tmp) / "bin"
    bindir.mkdir(exist_ok=True)
    for name in dict.fromkeys((*SUPPORT, *present)):
        real = shutil.which(name)
        target = bindir / name
        if real:
            target.symlink_to(real)
        else:
            target.write_text("#!/bin/sh\nexit 0\n")
            target.chmod(0o755)
    hostname = bindir / "hostname"
    hostname.write_text(f"#!/bin/sh\necho {host}\n")
    hostname.chmod(0o755)
    env = {**os.environ, "PATH": str(bindir), "HOME": str(Path(tmp) / "home")}
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def run(repo, *args, env):
    return subprocess.run(
        ["bash", str(repo / "aconf.sh"), *args],
        capture_output=True, text=True, env=env, timeout=30,
    )


def write_executable(path, body):
    if path.exists() or path.is_symlink():
        path.unlink()
    path.write_text(body)
    path.chmod(0o755)


def recording_env(tmp, *, snapshot_failure=False, apply_failure=False, user_reload_failure=False,
                  bootstrap_missing="", download_failure=False, installer_failure=False,
                  refresh_failure=False):
    env = stub_env(tmp, present=(*BASE_PREREQUISITES, *APPLY_PREREQUISITES))
    bindir = Path(env["PATH"])
    log = Path(tmp) / "commands.log"
    env.update({
        "COMMAND_LOG": str(log),
        "FAIL_SNAPSHOT": "1" if snapshot_failure else "0",
        "FAIL_APPLY": "1" if apply_failure else "0",
        "FAIL_USER_RELOAD": "1" if user_reload_failure else "0",
        "BOOTSTRAP_MISSING": bootstrap_missing,
        "FAIL_DOWNLOAD": "1" if download_failure else "0",
        "FAIL_INSTALLER": "1" if installer_failure else "0",
        "FAIL_REFRESH": "1" if refresh_failure else "0",
    })
    write_executable(bindir / "aconfmgr", r'''#!/bin/bash
printf 'aconfmgr %s\n' "$*" >> "$COMMAND_LOG"
if [[ " $* " == *" apply "* && "$FAIL_APPLY" == 1 ]]; then exit 1; fi
exit 0
''')
    write_executable(bindir / "sudo", r'''#!/bin/sh
printf 'sudo %s\n' "$*" >> "$COMMAND_LOG"
if [ "$1" = timeshift ] && [ "$2" = --create ] && [ "$FAIL_SNAPSHOT" = 1 ]; then exit 1; fi
if [ "$1" = bash ] && [ "$FAIL_INSTALLER" = 1 ]; then exit 1; fi
if [ "$1" = pacman ] && [ "$FAIL_REFRESH" = 1 ]; then exit 1; fi
exit 0
''')
    write_executable(bindir / "pacman-conf", '''#!/bin/sh
[ "$BOOTSTRAP_MISSING" != repository ]
''')
    write_executable(bindir / "pacman", '''#!/bin/sh
if [ "$1" = -Sl ] && [ "$BOOTSTRAP_MISSING" = database ]; then exit 1; fi
if [ "$1" = -Q ] && [ "$BOOTSTRAP_MISSING" = package ]; then exit 1; fi
exit 0
''')
    write_executable(bindir / "curl", '''#!/bin/sh
printf 'curl %s\\n' "$*" >> "$COMMAND_LOG"
[ "$FAIL_DOWNLOAD" != 1 ]
''')
    write_executable(bindir / "systemctl", r'''#!/bin/sh
if [ "$1" = --user ]; then
    printf 'user-systemctl-env %s %s\n' "$XDG_RUNTIME_DIR" "$DBUS_SESSION_BUS_ADDRESS" >> "$COMMAND_LOG"
fi
printf 'systemctl %s\n' "$*" >> "$COMMAND_LOG"
if [ "$*" = '--user daemon-reload' ] && [ "$FAIL_USER_RELOAD" = 1 ]; then exit 1; fi
exit 0
''')
    return env, log


class WrapperTest(unittest.TestCase):
    @arch_only
    def test_unknown_personal_host_is_refused_before_prerequisites(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = fake_repo(tmp, personal=("someone-else",), bypass_scope=False)
            result = run(repo, "lint", env=stub_env(tmp, present=()))
            self.assertEqual(result.returncode, 2)
            self.assertIn("not in personal-hosts", result.stderr)
            self.assertNotIn("missing prerequisites", result.stderr)


class ApplyTest(unittest.TestCase):
    def run_apply(self, tmp, input_text, *, missing_user_bus_env=False, **failures):
        repo = fake_repo(tmp)
        env, log_path = recording_env(tmp, **failures)
        if missing_user_bus_env:
            env.pop("XDG_RUNTIME_DIR", None)
            env.pop("DBUS_SESSION_BUS_ADDRESS", None)
        result = run_pty(["bash", str(repo / "aconf.sh"), "apply"], env=env, input_text=input_text)
        log = log_path.read_text().splitlines() if log_path.exists() else []
        return result, log

    def test_apply_requires_a_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = fake_repo(tmp)
            env, _ = recording_env(tmp)
            result = run(repo, "apply", env=env)
            self.assertEqual(result.returncode, 2)
            self.assertIn("interactive terminal", result.stderr)

    def test_default_refusal_stops_before_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, log = self.run_apply(tmp, "\n")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("[y/N]", result.stdout)
            self.assertIn("confirmation refused", result.stdout)
            self.assertFalse(any("timeshift --create" in line for line in log), log)
            self.assertFalse(any(line.startswith("curl ") for line in log), log)

    def test_snapshot_precedes_apply_and_manager_reloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, log = self.run_apply(tmp, "y\n")
            self.assertEqual(result.returncode, 0, result.stdout)
            def pos(f): return next(i for i, line in enumerate(log) if f in line)
            self.assertLess(pos("sudo timeshift --create"), pos("--color never apply"))
            self.assertLess(pos("--color never apply"), pos("sudo locale-gen"))
            self.assertLess(pos("sudo locale-gen"), pos("sudo systemctl daemon-reload"))
            self.assertLess(pos("sudo systemctl daemon-reload"), pos("systemctl --user daemon-reload"))
            self.assertFalse(any(" restart " in f" {l} " for l in log), log)
            self.assertFalse(any(line.startswith("curl ") or line.startswith("sudo bash ") for line in log), log)

    def test_bootstrap_precedes_apply_and_cleans_download(self):
        for missing in ("repository", "database", "package"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                result, log = self.run_apply(tmp, "y\n", bootstrap_missing=missing)
                self.assertEqual(result.returncode, 0, result.stdout)
                def pos(fragment): return next(i for i, line in enumerate(log) if fragment in line)
                self.assertLess(pos("timeshift --create"), pos("curl "))
                self.assertLess(pos("curl "), pos("sudo bash "))
                self.assertLess(pos("sudo bash "), pos("sudo pacman -Syu --needed chatgpt-bin"))
                self.assertLess(pos("sudo pacman "), pos("--color never apply"))
                installer = log[pos("sudo bash ")].removeprefix("sudo bash ")
                self.assertFalse(Path(installer).exists())

    def test_bootstrap_failures_stop_apply(self):
        for failure in ("download_failure", "installer_failure", "refresh_failure"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                result, log = self.run_apply(tmp, "y\n", bootstrap_missing="repository", **{failure: True})
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(any(line.startswith("aconfmgr ") for line in log), log)
                self.assertFalse(any("locale-gen" in line for line in log), log)
                download = next(line for line in log if line.startswith("curl "))
                installer = download.split(" -o ")[1].split()[0]
                self.assertFalse(Path(installer).exists())

    def test_snapshot_failure_stops_before_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, log = self.run_apply(tmp, "y\n", snapshot_failure=True)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertTrue(any("timeshift --create" in line for line in log), log)
            self.assertFalse(any(line.startswith("aconfmgr ") for line in log), log)
            self.assertFalse(any(line.startswith("curl ") for line in log), log)

    def test_apply_failure_stops_before_postflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, log = self.run_apply(tmp, "y\n", apply_failure=True)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertTrue(any(line.startswith("aconfmgr ") for line in log), log)
            self.assertFalse(any("locale-gen" in line or "systemctl" in line for line in log), log)

    def test_user_manager_reload_derives_missing_bus_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, log = self.run_apply(tmp, "y\n", missing_user_bus_env=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            expected = f"user-systemctl-env /run/user/{os.getuid()} unix:path=/run/user/{os.getuid()}/bus"
            self.assertIn(expected, log)

    def test_user_manager_reload_failure_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, _ = self.run_apply(tmp, "y\n", user_reload_failure=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("will load the global units at next start", result.stdout)


class ConfigTest(unittest.TestCase):
    def test_aconfmgr_config_files_parse(self):
        sources = sorted(ACONFMGR_CONFIG.glob("*.sh"))
        sources.extend(sorted((ACONFMGR_CONFIG / "hosts").iterdir()))
        self.assertTrue(sources)
        for path in sources:
            with self.subTest(path=path.name):
                result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_dynamic_scope_registers_synthetic_local_path(self):
        script = r'''
set -e
ignore_paths=()
IgnorePath() { ignore_paths+=("$1"); }
AddPackage() { :; }
CopyFile() { :; }
CopyFileTo() { :; }
CreateLink() { :; }
SetFileProperty() { :; }
config_dir="$1"
source "$config_dir/00-scope.sh"
source "$config_dir/30-system.sh"
source "$config_dir/hosts/lightshow"
CopyFile "/etc/synthetic-private-local.conf"
pacman() { printf '%s\n' /etc/synthetic-deleted.conf /etc/synthetic-private-local.conf /etc/synthetic-deleted-dir/; }
source "$config_dir/99-scope.sh"
is_ignored() { local p="$1" pat; for pat in "${ignore_paths[@]}"; do [[ "$p" == $pat ]] && return 0; done; return 1; }
[[ " ${_aconf_managed[*]} " == *" /etc/synthetic-private-local.conf "* ]]
! is_ignored /etc/synthetic-private-local.conf
! is_ignored /etc/systemd
! is_ignored /etc/systemd/system
! is_ignored /etc/systemd/system/grub-btrfsd.service.d/override.conf
is_ignored /etc/os-release
is_ignored /etc/synthetic-deleted.conf
is_ignored /etc/synthetic-deleted-dir/child
'''
        result = subprocess.run(["bash", "-c", script, "bash", str(ACONFMGR_CONFIG)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_scope_enumeration_failures_abort(self):
        for failure in ("pacman", "find"):
            with self.subTest(failure=failure):
                script = r'''
set -e
ignore_paths=()
IgnorePath() { ignore_paths+=("$1"); }
FatalError() { printf '%s' "$1" >&2; exit 9; }
pacman() { printf '%s\n' /etc/synthetic-deleted.conf; }
if [[ "$2" == pacman ]]; then
    pacman() { echo 'package enumeration failed' >&2; return 1; }
else
    find() { printf '/etc/partial\0'; echo 'filesystem enumeration failed' >&2; return 1; }
fi
source "$1/00-scope.sh"
source "$1/99-scope.sh"
echo UNSAFE_CONTINUATION
'''
                result = subprocess.run(
                    ["bash", "-c", script, "bash", str(ACONFMGR_CONFIG), failure],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 9, result.stderr)
                self.assertIn("enumeration failed", result.stderr)
                self.assertNotIn("UNSAFE_CONTINUATION", result.stdout)

    def run_dispatch(self, host):
        script = r'''
set -e
warnings=0
ConfigWarning() { warnings=$((warnings+1)); }
Color() { :; }
FatalError() { echo "unexpected FatalError" >&2; exit 9; }
AddPackage() { packages+=("$2$1"); }
CopyFileTo() { :; }
CreateLink() { :; }
SetFileProperty() { :; }
packages=()
config_dir="$1"
want_host="$2"
hostname() { echo "$want_host"; }
source "$config_dir/90-host.sh"
printf 'warnings=%s packages=%s\n' "$warnings" "${#packages[@]}"
'''
        return subprocess.run(
            ["bash", "-c", script, "bash", str(ACONFMGR_CONFIG), host],
            capture_output=True, text=True,
        )

    def test_declared_host_with_overlay_loads_it_without_warning(self):
        result = self.run_dispatch("lightshow")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warnings=0", result.stdout)
        self.assertNotIn("packages=0", result.stdout)

    def test_host_without_overlay_warns_instead_of_failing(self):
        # A fresh machine must converge against common intent before anyone has
        # written its host file. The warning is the reminder to write one.
        result = self.run_dispatch("no-such-host")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("warnings=1", result.stdout)
        self.assertIn("packages=0", result.stdout)

    def test_local_and_capture_artifacts_are_gitignored(self):
        for rel in ("aconf.local.sh", "aconfmgr/aconfmgr.local", "aconfmgr/99-unsorted.sh"):
            with self.subTest(path=rel):
                result = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT)
                self.assertEqual(result.returncode, 0, f"{rel} is not gitignored")


if __name__ == "__main__":
    unittest.main()
