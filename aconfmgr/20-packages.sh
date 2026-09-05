# Common explicit package intent for declared personal Arch hosts.
#
# Packages are grouped by purpose. Host-specific packages belong in hosts/.
# Keep the aconfmgr toolchain explicit: apply demotes omitted packages and prunes
# resulting orphans.

# Base system and build chain.
AddPackage base
AddPackage base-devel
AddPackage git
AddPackage linux
AddPackage linux-firmware
AddPackage man-db
AddPackage sudo

# aconfmgr runtime dependencies.
AddPackage pacutils
AddPackage expect
AddPackage python

# Package management.
AddPackage flatpak
AddPackage pkgstats
AddPackage rebuild-detector
AddPackage reflector
AddPackage --foreign yay
AddPackage --foreign aconfmgr-git

# Boot and rollback.
AddPackage btrfs-progs
AddPackage cronie
AddPackage efibootmgr
AddPackage grub
AddPackage grub-btrfs
AddPackage timeshift
AddPackage --foreign timeshift-autosnap

# Hardware inspection and power management.
AddPackage dmidecode
AddPackage fwupd
AddPackage i2c-tools
AddPackage power-profiles-daemon
AddPackage wireless-regdb

# Networking and remote access.
AddPackage axel
AddPackage cloudflared
AddPackage freerdp
AddPackage mosh
AddPackage networkmanager
AddPackage nm-connection-editor
AddPackage openssh
AddPackage rclone
AddPackage remmina
AddPackage samba
AddPackage tailscale
AddPackage ufw
AddPackage --foreign eternalterminal
AddPackage --foreign onedrive-abraunegg

# Audio and video.
AddPackage alsa-utils
AddPackage cava
AddPackage gst-plugins-good
AddPackage libva-utils
AddPackage pipewire
AddPackage pipewire-alsa
AddPackage pipewire-jack
AddPackage pipewire-pulse
AddPackage rtkit
AddPackage vulkan-tools

# Desktop session.
AddPackage dms-shell
AddPackage quickshell
AddPackage hyprland
AddPackage greetd
AddPackage uwsm
AddPackage --foreign greetd-dms-greeter-git

# Resolve virtual desktop dependencies without interactive provider prompts.
AddPackage gnome-keyring
AddPackage qt6-multimedia-ffmpeg
AddPackage wireplumber
AddPackage xdg-desktop-portal-gtk

# Desktop shell and display configuration.
AddPackage brightnessctl
AddPackage dgop
AddPackage matugen
AddPackage nwg-displays
AddPackage --foreign dankcalendar-bin
AddPackage --foreign dsearch-bin

# Desktop applications and GTK/Qt integration.
AddPackage adw-gtk-theme
AddPackage exo
AddPackage gnome-disk-utility
AddPackage kdeconnect
AddPackage kimageformats
AddPackage nautilus
# DMS generates KDE color schemes for Qt applications.
AddPackage --foreign qt6ct-kde

# Terminal environment.
AddPackage fish
AddPackage ghostty
AddPackage helix
AddPackage jq
AddPackage starship
AddPackage tmux
AddPackage zellij

# Command-line utilities.
AddPackage bitwarden-cli
AddPackage fastfetch
AddPackage inotify-tools
AddPackage zip

# Fonts.
AddPackage noto-fonts
AddPackage noto-fonts-cjk
AddPackage noto-fonts-emoji
AddPackage noto-fonts-extra
AddPackage ttf-jetbrains-mono
AddPackage ttf-nerd-fonts-symbols
AddPackage ttf-recursive-nerd
AddPackage --foreign ttf-gabarito-git
AddPackage --foreign ttf-roboto-flex

# Development and content toolchains.
AddPackage bun
AddPackage clang
AddPackage cmake
AddPackage dmd
AddPackage fontforge
AddPackage git-lfs
AddPackage github-cli
AddPackage go
AddPackage java-runtime-common
AddPackage jdk-openjdk
AddPackage lazygit
AddPackage meson
AddPackage nodejs-lts-jod
AddPackage npm
AddPackage python-html5lib
AddPackage python-psutil
AddPackage rustup
AddPackage shellcheck
AddPackage uv

# Agent and assistant tooling.
AddPackage openai-codex
AddPackage opencode
AddPackage --foreign antigravity-cli
AddPackage --foreign claude-desktop

# Browsers and communication.
AddPackage bitwarden
AddPackage discord
AddPackage firefox
AddPackage signal-desktop
AddPackage --foreign google-chrome
# Zoom, with the Qt runtimes it optionally loads.
AddPackage --foreign zoom
AddPackage --foreign qt5-remoteobjects
AddPackage --foreign qt5-webengine

# Gaming.
AddPackage gamescope
AddPackage lib32-harfbuzz
AddPackage lib32-libpulse
AddPackage lutris
AddPackage steam
AddPackage --foreign minecraft-launcher
AddPackage --foreign protonplus

# Peripherals.
AddPackage bluez
AddPackage bluez-utils
AddPackage --foreign uhk-agent-appimage

# Printing.
AddPackage cups
AddPackage cups-pdf
AddPackage cups-pk-helper
AddPackage print-manager
AddPackage system-config-printer

# Documents, media and writing.
AddPackage dcraw
AddPackage docx2txt
AddPackage harper
AddPackage khal
AddPackage obsidian
AddPackage spotify-launcher

# TeX Live.
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
