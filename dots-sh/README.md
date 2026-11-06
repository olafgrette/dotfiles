# dots.oag.sh

Workers Static Assets serves `init.sh` at `/` and approved third-party files
under `/assets/`. There is no request Worker, R2 bucket, or client authentication.
Do not enable the optional Workers Cache feature: static delivery is already
free; that feature introduces request charges. Each file must fit the 25 MiB
static-asset limit.

`artifacts.json` holds source URLs, SHA-256 hashes, immutable served paths, and
the current selection for each installer input. `public/` is ignored. Clients
fetch from this host only, verify hashes before replacement or execution, and
preserve the previous file if a download fails. Existing Starship installations
are left alone; missing Starship installs use the approved platform archive and
write to `~/.local/bin/starship` without sudo.

The mirror covers Starship's Unix release archives, zellij-choose-tree, the
Ghostty shader, the OpenAI Arch bootstrap script, and CORVIAN's Brood War
cursor pack for Linux (version 1.0). License notices accompany
the open-source assets. The OpenAI script still uses the vendor's signed package
repository. Git clones, Dux plugin Git repositories, OS packages, and GitHub
itself remain external dependencies. Foreground Linux GUI installs place the
cursor pack at `${XDG_DATA_HOME:-$HOME/.local/share}/icons/broodwar` without selecting
it. Background, headless, and macOS installs skip it. A hash receipt avoids
repeated downloads. Replacements preserve the previous theme as `broodwar.bak`;
an existing backup stops replacement until resolved. Its original archive is
preserved intact in the mirror. KDE Store tags it `mit-license`, but the archive
contains no standalone license notice.

## Deploy

```sh
npx --yes wrangler@4 login  # only when the saved Cloudflare login needs renewal
python3 dots-sh/artifacts.py stage
./dots-sh/deploy.sh check
./dots-sh/deploy.sh deploy
```

Staging restores missing files from the live mirror and reuses verified local
files. For an initial deployment or newly approved entries that are not live,
use `python3 dots-sh/artifacts.py stage --upstream` after reviewing their sources
and hashes. Entries with `source_type: ocs` resolve a fresh KDE Store download link
from the recorded metadata endpoint; expiring URLs never enter the manifest.
Deployment stages again, publishes, then verifies every live hash.
`./dots-sh/deploy.sh verify` repeats only the live verification.

The bootstrap is now a deployed copy of this checkout's `init.sh`. Changing it
requires a deploy; pushing Git alone no longer updates `/`. Deploy reviewed
bootstrap changes only when the matching repository changes are available to
fresh clones. The initial migration uses the unchanged, already published script.

## Update an artifact

1. Review the upstream change and its redistribution terms. Download into a
   temporary directory. Compare an upstream checksum when supplied; otherwise
   record that the hash pins the retrieved bytes, not an independent signature.
2. Add a new entry to `files` with a new version or full content-hash path.
   Preserve old entries and paths so older dotfiles checkouts still work. Include
   the applicable license notice. Change the corresponding `current` selection.
3. Stage and check. Inspect the manifest diff and the payloads before deployment.
   Staging refuses unexpected files or symlinks in `public/`.
4. Deploy and verify before publishing the client manifest change to Git. Do not
   push clients that refer to files which have not passed live verification.

Retained entries allow any checkout to rebuild the complete deployment from the
mirror. Keep a backup of `public/` if recovery must survive both the mirror and
upstream disappearing. A stale checkout must not deploy: it would omit newer
retained versions. First update to current main and review its manifest.

Upload authorization is the machine-local Wrangler login. No credential is put
in Git or required on downloading machines. This workflow has no custom signing
service, release branches, or SSH authentication gateway.
