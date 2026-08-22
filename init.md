# Setting up a machine

Operational notes for `init.sh`, `aconf.sh`, and the Arch system layer. The
README covers what this repository is; this file covers what to type.

## Layers

- `install.sh` — the portable `$HOME` layer. Runs on every host: macOS, work,
  remote, unknown. Degrades safely and never touches the system.
- `aconf.sh` — the Arch system layer: explicit packages, reviewed `/etc`, unit
  enablement. Refuses any host not listed in `personal-hosts`, and any host
  that is not Arch.
- `init.sh` — once per box. Runs the system layer, then `dms setup`, then
  `install.sh`.

Declarations live in `aconfmgr/`, at the top level rather than under `.config/`,
because they are not part of the `$HOME` mirror and were never linked into it.

## Fresh personal Arch host

Declared hosts are in `personal-hosts` — currently `lightshow`, `olafmbp`,
`olafmbp-linux`, `olafx1c`.

1. **Set the hostname first.** `sudo hostnamectl set-hostname <short>`.
   `init.sh` refuses to run as root, before the hostname is set, or on a host
   absent from `personal-hosts`.
2. **Btrfs root with a configured Timeshift.** `apply` creates a snapshot
   before it changes anything and aborts if that fails. Timeshift's own
   configuration is not managed — set it up by hand.
3. **Clean up orphans before the first apply.** aconfmgr prunes orphaned
   packages recursively, so anything left over from installation gets swept as
   a side effect of convergence. Do it deliberately instead:

   ```sh
   pacman -Qdtq | sudo pacman -Rns -
   ```

4. **Run it.**

   ```sh
   curl -fsSL https://raw.githubusercontent.com/olafgrette/dotfiles/main/init.sh | sh
   ```

   It clones over HTTPS if needed, delegates to `aconf.sh apply`, stops to ask
   for `dms setup` if `~/.config/hypr` is missing, then runs `install.sh`.
   An existing `~/dotfiles` is left alone; it prints the `git remote set-url`
   to flip to SSH.

5. **Enable what stays manual.** Nothing here starts or restarts services.
   The Drive mount in particular needs a credential this repository does not
   contain:

   ```sh
   rclone config          # create the gdrive: remote
   systemctl --user enable --now rclone-gdrive.service
   ```

## What the first apply writes

Eleven of the twelve managed objects are common intent, so a fresh host gets
almost all of them on the first run. Two are worth knowing about in advance:

- **`/etc/pacman.conf`** is replaced with this repository's copy — the current
  pacnew with `[multilib]` enabled. Extra repositories configured on the new
  machine would be overwritten.
- **`/etc/locale.gen`** is reduced to the single `en_US.UTF-8` line. `aconf.sh`
  runs `locale-gen` in its postflight, so the locale is regenerated
  immediately.

`aconfmgr --paranoid apply` prompts before every individual change, so both are
visible before they happen.

## Host intent

A declared host with no file under `aconfmgr/hosts/` converges against common
intent alone and prints a warning — a new machine must be able to bootstrap
before anyone has written its host file. Write the overlay afterward.

Only hardware belongs there. `hosts/lightshow` is AMD microcode, the NVIDIA
stack, Xorg helpers and virtualization; `hosts/olafx1c` is Intel microcode and
the userspace half of Intel Arc graphics. Everything else — locale, timezone,
pacman, FUSE, greetd, the Timeshift scheduler, boot entries — is common.

## Other hosts

Fedora, macOS, unknown:

```sh
git clone https://github.com/olafgrette/dotfiles.git ~/dotfiles
~/dotfiles/install.sh
./readiness.sh
```

No system layer. `readiness.sh` reports what is missing without installing it.

## Day to day

```sh
./aconf.sh lint     # compile and lint the configuration
./aconf.sh diff     # managed-file drift; packages are not included
./aconf.sh save     # capture inverse drift to aconfmgr/99-unsorted.sh
./aconf.sh apply    # snapshot, confirm, converge
```

`save` writes what the system has that the configuration does not. Review
`99-unsorted.sh`, move anything wanted into real declarations, and empty it —
`apply` should never run with unsorted intent outstanding.

`diff` compares file contents and symlinks only. It does not compare packages,
and it does not compare file modes. Those need checking separately:

```sh
comm -3 <(pacman -Qeq | sort) <(grep -h '^AddPackage' aconfmgr/20-packages.sh \
    aconfmgr/30-system.sh aconfmgr/hosts/$(uname -n) \
    | sed 's/AddPackage --foreign //;s/AddPackage //' | sort)
```

Empty output means declared intent and installed explicit packages agree.

## If an apply goes wrong

Nothing restores automatically. `aconf.sh` creates a Timeshift snapshot
commented `pre-aconfmgr-<host>-<timestamp>` before it touches anything.

```sh
sudo timeshift --list
sudo timeshift --restore --snapshot '<name>'
```

The transaction does not modify the EFI bootloader, so the restore does not
need to rewrite it. On lightshow `/home` is a separate `@home` subvolume
excluded from backup, so a restore reverts the system and the package database
without touching `$HOME` — verify that holds on any other machine before
relying on it.

## Secrets

The repository is public and `aconfmgr/99-scope.sh` is fail-closed: every
`/etc` path is ignored unless a declaration registers it. That is deliberate,
and it is what keeps `/etc/cloudflared/`, the ufw rules, `sshd_config`, and
network configuration out.

Credentials live outside the repository and are set up by hand on each machine:
`~/.config/rclone/rclone.conf`, tailscale state, cloudflared tunnel
credentials, SSH host keys.
