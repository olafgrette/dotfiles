# Common explicit package intent for declared personal Arch hosts.
#
# This remains a curated portable set rather than a captured manifest. Entries
# are public only when they are required by bootstrap or tracked configuration,
# or Olaf explicitly approved them for every managed Arch host. Everything
# else stays in a host overlay or the ignored aconfmgr.local.
#
# The seed is not optional. aconfmgr demotes every explicit package absent from
# the configuration and prunes the resulting orphans, so an apply omitting its
# own toolchain removes the tooling that is running it.

# Base system and build chain. base-devel provides makepkg for AUR builds.
AddPackage base
AddPackage base-devel
AddPackage git
AddPackage sudo

# aconfmgr's runtime chain. pacutils, expect and python are declared because
# paccheck, unbuffer and dms-settings are direct bootstrap requirements — that
# holds regardless of what else happens to depend on them. grep, gawk and
# diffutils are equally required but ship with base and pacman, so they stay
# dependencies rather than adding permanent inverse drift.
AddPackage pacutils
AddPackage expect
AddPackage python

# Rollback substrate, required before any apply.
AddPackage btrfs-progs
AddPackage timeshift
AddPackage cronie

# Portable development and content toolchains.
AddPackage dmd
AddPackage fontforge
AddPackage go
AddPackage meson
AddPackage npm
AddPackage rustup

# Printing is expected on every managed Arch host.
AddPackage cups
AddPackage cups-pdf
AddPackage cups-pk-helper
AddPackage print-manager
AddPackage system-config-printer

# Full TeX Live collection retained as explicit portable intent.
AddPackage texlive-basic
AddPackage texlive-bibtexextra
AddPackage texlive-binextra
AddPackage texlive-context
AddPackage texlive-fontsextra
AddPackage texlive-fontsrecommended
AddPackage texlive-fontutils
AddPackage texlive-formatsextra
AddPackage texlive-games
AddPackage texlive-humanities
AddPackage texlive-latex
AddPackage texlive-latexextra
AddPackage texlive-latexrecommended
AddPackage texlive-luatex
AddPackage texlive-mathscience
AddPackage texlive-metapost
AddPackage texlive-music
AddPackage texlive-pictures
AddPackage texlive-plaingeneric
AddPackage texlive-pstricks
AddPackage texlive-publishers
AddPackage texlive-xetex

# Referenced by tracked configuration: install.sh, config.fish, ghostty/config.
AddPackage fish
AddPackage jq
AddPackage helix
AddPackage tmux
AddPackage zellij
AddPackage starship
AddPackage ghostty
AddPackage ttf-jetbrains-mono
AddPackage ttf-recursive-nerd

# GUI profile core, required by the bootstrap postflight contract.
AddPackage dms-shell
AddPackage quickshell
AddPackage hyprland
AddPackage greetd

# The AUR helper and the provisioner itself.
AddPackage --foreign yay
AddPackage --foreign aconfmgr-git
AddPackage --foreign greetd-dms-greeter-git
AddPackage --foreign ttf-gabarito-git
AddPackage --foreign ttf-roboto-flex
AddPackage --foreign uhk-agent-appimage
