# dotfiles

My personal configuration files.

Or, more accurately:

> A bespoke cross-platform configuration management system I built because using a dotfile manager would have been overengineering.

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

## Installation

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

Yes, `curl | sh`. It fetches `init.sh` out of this repository. Served through a cloudflare worker which reads and returns the github raw content. The source for which is in this repository. This dotfile repository.

It clones, converges the Arch system layer if the machine is one of mine, and then runs `install.sh`.

The parts that are still manual, and the ones worth reading before pointing this at a machine you like, are in [init.md](init.md).

## Architecture

Repository paths mostly mirror `$HOME`.

```text
.config/fish       -> ~/.config/fish
.config/ghostty    -> ~/.config/ghostty
.config/helix      -> ~/.config/helix
```

Revolutionary stuff.

There is deliberately no abstraction layer between the files and where the files go, except for `install.sh`, several helper scripts, generated configuration, host-specific behavior, platform-specific behavior, local overrides, and background synchronization.

Again: not a dotfile manager.

## Continuous deployment

Every interactive shell spawned (5 minute cooldown) will, in a backgrounded asynchronous fashion, pull this repository and run `install.sh` to converge my config toward the desired state.

It also synchronizes agent skills each time, because apparently once was not enough.

This is a perfectly reasonable thing to do in your manager-less dotfiles.

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

## Scoping

There are separate personal/work scopes and local-only-non-committed config file options because accidentally putting employer-specific configuration into a public Git repository is traditionally considered suboptimal.

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

## Supported environments

Nominally:

* macOS
* Linux desktops
* headless Linux machines

## Should you use these?

Probably not.

Dotfiles are the software equivalent of someone's custom keyboard layout: interesting to inspect, occasionally useful to steal from, and deeply suspicious as a complete lifestyle adoption.

Feel free to copy anything useful.
