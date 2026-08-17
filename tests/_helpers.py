"""Shared helpers for aconf/init black-box tests — factored to deduplicate harness."""

from pathlib import Path
import os
import pty
import select
import subprocess
import time
import unittest


def distro_id():
    release = Path("/etc/os-release")
    if not release.exists():
        return ""
    for line in release.read_text().splitlines():
        if line.startswith("ID="):
            return line[3:].strip().strip('"')
    return ""


arch_only = unittest.skipUnless(distro_id() == "arch", "Arch-only scope gate")


def run_pty(cmd, env, input_text="", timeout=30):
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        cmd,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=env,
        close_fds=True,
    )
    os.close(slave)
    if input_text:
        os.write(master, input_text.encode())
    chunks = []
    deadline = time.monotonic() + timeout
    while proc.poll() is None or select.select([master], [], [], 0)[0]:
        if time.monotonic() >= deadline:
            proc.kill()
            proc.wait()
            os.close(master)
            raise subprocess.TimeoutExpired(proc.args, timeout)
        ready, _, _ = select.select([master], [], [], 0.05)
        if not ready:
            continue
        try:
            chunk = os.read(master, 65536)
        except OSError:
            break
        if chunk:
            chunks.append(chunk)
    os.close(master)
    return subprocess.CompletedProcess(
        proc.args, proc.wait(), stdout=b"".join(chunks).decode(errors="replace"), stderr=""
    )
