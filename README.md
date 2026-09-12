# dotfiles

My personal configuration files.

Some of them live in `$HOME`.

Some of them live in `/etc`.

Some of them are packages and systemd units.

These are all dotfiles.

## Philosophy

No Stow.
No chezmoi.
No plugin-manager cinematic universe.

Just symlinks, shell scripts, and the firm belief that `install.sh` is not a dotfile manager if I refuse to call it one.

The general rule is:

> If a tool needs 900 lines of configuration and seventeen plugins before it becomes pleasant to use, perhaps the problem is the tool.

Current winners include:

* shell: **fish**
* prompt: **starship**
* terminal emulator: **ghostty**
* terminal multiplexer: **zellij**
* editor: **helix**
* window manager: **hyprland**
* desktop environment: **DankMaterialShell**
* an increasingly unreasonable number of AI agent harnesses

## Architecture

There are two configuration layers and a bootstrap script.

```text
init.sh
├── aconf.sh
│   └── aconfmgr
│       ├── packages
│       ├── selected /etc
│       ├── systemd state
│       └── per-host hardware intent
│
└── install.sh
    └── $HOME
```

### `$HOME`

`install.sh` is the portable layer.

Repository paths mostly mirror `$HOME`:

```text
.config/fish       -> ~/.config/fish
.config/ghostty    -> ~/.config/ghostty
.config/helix      -> ~/.config/helix
```

It runs on macOS, personal Linux machines, work machines, remote hosts, and unknown hosts, degrading safely when optional software is absent.

This is the normal dotfile part.

### The other dotfiles

Personal Arch machines also get an `aconfmgr` layer.

That describes things which are not technically in `$HOME`, including:

* explicit package state
* selected `/etc` files
* locale configuration
* pacman configuration
* systemd unit enablement
* boot-related configuration
* per-host hardware packages

`aconf.sh` wraps that layer with host gating, safety checks, snapshots, and the small amount of postflight work required to make written configuration active.

This is also the normal dotfile part.

The files are simply farther away from `$HOME`.

### Bootstrap

`init.sh` exists for a machine that is not configured yet.

On one of my personal Arch machines it runs:

```text
aconf.sh apply
       ↓
dms setup, if needed
       ↓
install.sh
```

On everything else it just installs the portable `$HOME` layer.

So yes, `init.sh` is an idempotent orchestration layer over separate user-state and system-state convergence mechanisms.

This should not be confused with configuration management.

It is a shell script that makes sure my files are where I want them.

Some of the files just happen to be the operating system.

### Why not Nix?

Because I still understand how my computer works.

### Why not Ansible?

Maintaining an inventory containing one guy's computers seemed excessive.

### Why not Chef?

I already write Chef at work and bringing enterprise configuration management home would constitute a failure to maintain appropriate work-life boundaries.

Instead I wrote this.

These are different things.

## Installation

If the repository is already present:

```sh
./install.sh
```

This will do normal dotfile things such as:

* create symlinks
* install starship if necessary
* configure Claude
* configure Gemini
* configure OpenCode
* configure Codex
* apply desktop settings
* enable systemd user lingering
* synchronize agent skills
* download a ghostty shader from the Internet

You know.

Dotfiles.

## Fresh machine

When the machine has nothing on it yet, not even this repository:

```sh
curl -fsSL dots.oag.sh | sh
```

Yes, `curl | sh`.

It fetches `init.sh` from this repository through a Cloudflare Worker whose source also lives in this repository.

This dotfile repository.

`init.sh` clones the repo if necessary, determines what kind of machine it is, and takes it from there.

On a declared personal Arch host that includes the system layer. On anything else it leaves the system alone and runs `install.sh`.

The remaining manual steps, along with the things worth reading before pointing this at a computer you particularly enjoy having operational, are in [init.md](init.md).

## System state

System declarations live under `aconfmgr/`.

Most configuration is common across my personal Arch machines. Hardware differences live in host overlays.

A new declared host does not need an overlay in order to bootstrap: common state applies first, and hardware-specific intent can be added afterward.

This avoids the somewhat inconvenient requirement that a newly installed machine already have a complete configuration describing the newly installed machine.

### Day to day

Normal dotfile maintenance:

```sh
./aconf.sh lint
./aconf.sh diff
./aconf.sh save
./aconf.sh apply
```

`lint` checks the declarations.

`diff` shows managed-file drift.

`save` captures inverse drift into `99-unsorted.sh` for review.

`apply` converges the machine.

The intended workflow after changing something manually is to inspect what `save` captured, promote anything intentional into the real declarations, discard the rest, and then apply.

Configuration drift should be reviewed before being accepted into Git.

This is an ordinary concern for dotfiles.

### Applying changes

Because some of these particular dotfiles can make the computer stop booting, `aconf.sh apply` is slightly cautious.

It:

* only runs the system layer on Arch
* refuses hosts not explicitly listed in `personal-hosts`
* requires an interactive terminal
* defaults confirmation to **no**
* creates a Timeshift snapshot before system mutation
* aborts if snapshot creation fails
* runs `aconfmgr apply` with normal change-group prompts
* regenerates locale state afterward
* reloads system and user systemd managers

There is deliberately no automatic rollback.

If an apply goes badly, the pre-apply Timeshift snapshot exists so restoration can be a conscious decision rather than another shell script making increasingly confident decisions about the machine.

The presence of rollback snapshots should not be interpreted as evidence that this has become infrastructure management.

Sometimes changing your dotfiles can make Linux unbootable.

Everyone knows this.

## Continuous deployment

Every interactive shell periodically checks this repository, subject to a cooldown, and asynchronously converges the portable user layer toward the current desired state.

It also synchronizes agent skills each time, because apparently once was not enough.

This means I can push configuration, open a shell on another machine, and eventually have that machine acquire the new desired state.

This is not continuous deployment.

Nothing has been deployed.

The files were already supposed to be there.

## AI governance

`UNIVERSAL_AGENT_DIRECTIVES.md` contains shared instructions rendered for multiple coding agents.

The same fundamental instructions are distributed to:

```text
Claude
Gemini
OpenCode
Codex
```

This prevents the exciting possibility of four different artificial intelligences independently deciding how I want them to behave.

There are also shared skills and scope-specific agent configuration.

Because apparently having opinions about terminal emulators wasn't enough; now the robots also need organizational policy.

## Scoping

There are separate personal/work scopes and local-only, non-committed configuration options because accidentally putting employer-specific configuration into a public Git repository is traditionally considered suboptimal.

The system layer is more paranoid.

Only personal Arch hosts explicitly listed in `personal-hosts` may receive it.

Managed `/etc` state is fail-closed: paths are ignored unless a declaration explicitly claims them.

There is host-specific configuration because different machines have different hardware.

This should not be confused with an inventory.

There is no inventory file.

Therefore there is no inventory.

## Secrets

Secrets do not live in this repository.

Personal file secrets can instead be materialized explicitly from Bitwarden with:

```sh
secret-sync pull
```

That process:

* requires a fresh vault unlock
* fetches current secret material
* validates it
* shows every destination it intends to modify
* defaults confirmation to **no**
* writes atomically
* locks the CLI vault again afterward

It is deliberately never invoked by `install.sh` or background convergence.

Other machine enrollment state also remains local and manual, including things such as OAuth tokens, Tailscale state, Cloudflare tunnel credentials, and SSH host keys.

So, approximately:

```text
public Git repository
        │
        ├── desired $HOME state
        ├── desired package state
        ├── desired selected /etc state
        ├── desired systemd state
        ├── desktop configuration
        ├── per-host hardware intent
        ├── bootstrap orchestration
        ├── convergence logic
        ├── agent policy
        ├── regression tests
        └── instructions for obtaining secrets
                    │
                    └── elsewhere
```

Again, this is a dotfiles repository.

The distinction is important.

## Tests

There are tests now.

```text
tests/
├── test_aconf.py
├── test_dms_settings.py
└── test_init.py
```

These are black-box tests for such ordinary dotfile concerns as:

* host eligibility
* distro gating
* bootstrap ordering
* prerequisite failures
* interactive confirmations
* rollback snapshot creation
* failure propagation
* system convergence
* desktop bootstrap behavior

The test suites for `aconf.sh` and `init.sh` are considerably larger than the scripts themselves.

This is good.

It means the dotfiles are well tested.

It does not mean the dotfiles have become software.

## Is my machine ready?

```sh
./readiness.sh
```

This checks whether the pile of software referenced by these dotfiles actually exists.

Possible results:

```text
✅ git
✅ fish
✅ ghostty
✅ helix
✅ claude
✅ codex
❌ whatever I installed at 2 AM and forgot about
```

It does not install missing software.

I still have some standards.

## Disaster recovery

A sufficiently blank replacement personal Arch machine can increasingly be turned back into something recognizable with:

```sh
curl -fsSL dots.oag.sh | sh
```

followed by restoring personal data, secrets, and the deliberately unmanaged pieces of machine enrollment state.

This works because the repository happens to contain the desired user configuration, system configuration, package inventory, service configuration, desktop configuration, host-specific machine intent, and the executable ordering required to recreate them.

It is not a disaster-recovery system.

It is simply useful after a disaster.

Please stop trying to make this weird.

## Supported environments

Nominally:

* macOS
* Linux desktops
* headless Linux machines

The portable `$HOME` layer is intended to work across all of them.

Personal Arch machines additionally receive the system layer.

Practically:

* my computers
* computers sufficiently similar to my computers
* your computer, briefly, before you realize you should fork this

## Should you use these?

Probably not.

Dotfiles are the software equivalent of someone's custom keyboard layout: interesting to inspect, occasionally useful to steal from, and deeply suspicious as a complete lifestyle adoption.

Feel free to copy anything useful.

If you run the bootstrap script wholesale on your own machine, however, you are not joining a managed fleet.

There is no fleet.

I only have a few computers.
