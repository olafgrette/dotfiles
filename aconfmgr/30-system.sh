# Common system intent for declared personal Arch hosts.

# Locale — LANG=en_US.UTF-8, one-line locale.gen.
CopyFile "/etc/locale.conf"
CopyFile "/etc/locale.gen"

# Timezone.
CreateLink "/etc/localtime" "/usr/share/zoneinfo/America/Los_Angeles"

# Pacman — stock pacnew with [multilib] enabled. Mirrors stay unmanaged.
CopyFile "/etc/pacman.conf"

# FUSE — user_allow_other, needed by the rclone and OneDrive mounts.
CopyFile "/etc/fuse.conf"

# PAM login limits — raise the hard nofile ceiling for PAM sessions.
CopyFile "/etc/security/limits.conf"

# Google Drive. Install and globally enable the user unit, but let its
# ConditionPathExists gate keep it inert until the user has enrolled rclone.
# The config and OAuth material remain user-owned state outside aconfmgr.
CopyFile "/etc/systemd/user/rclone-gdrive.service"
CreateLink "/etc/systemd/user/default.target.wants/rclone-gdrive.service" "/etc/systemd/user/rclone-gdrive.service"

# Timeshift snapshots.
CopyFile "/etc/cron.d/timeshift-hourly"
CreateLink "/etc/systemd/system/multi-user.target.wants/cronie.service" "/usr/lib/systemd/system/cronie.service"

# Arch's stock root directory mode.
SetFileProperty / mode 555

# Snapshot boot entries. The drop-in resets ExecStart before --timeshift-auto
# --syslog; the vendor unit ships disabled. Bootstrap enforces the shadow-unit
# absence this link needs, after its rollback snapshot.
CopyFile "/etc/systemd/system/grub-btrfsd.service.d/override.conf"
CreateLink "/etc/systemd/system/multi-user.target.wants/grub-btrfsd.service" "/usr/lib/systemd/system/grub-btrfsd.service"

# Printing. cups.socket is the on-demand activation path and cups.path picks
# up spooled jobs, so all four links are the enablement.
CreateLink "/etc/systemd/system/multi-user.target.wants/cups.service" "/usr/lib/systemd/system/cups.service"
CreateLink "/etc/systemd/system/multi-user.target.wants/cups.path" "/usr/lib/systemd/system/cups.path"
CreateLink "/etc/systemd/system/printer.target.wants/cups.service" "/usr/lib/systemd/system/cups.service"
CreateLink "/etc/systemd/system/sockets.target.wants/cups.socket" "/usr/lib/systemd/system/cups.socket"

# Bluetooth. The hardware condition in the vendor unit makes this a no-op on
# hosts without a Bluetooth controller. The alias permits D-Bus activation.
CreateLink "/etc/systemd/system/bluetooth.target.wants/bluetooth.service" "/usr/lib/systemd/system/bluetooth.service"
CreateLink "/etc/systemd/system/dbus-org.bluez.service" "/usr/lib/systemd/system/bluetooth.service"

# NetworkManager. Left unmanaged, a fresh host comes up with no network. The
# dbus alias is what enabling the dispatcher writes.
CreateLink "/etc/systemd/system/multi-user.target.wants/NetworkManager.service" "/usr/lib/systemd/system/NetworkManager.service"
CreateLink "/etc/systemd/system/network-online.target.wants/NetworkManager-wait-online.service" "/usr/lib/systemd/system/NetworkManager-wait-online.service"
CreateLink "/etc/systemd/system/dbus-org.freedesktop.nm-dispatcher.service" "/usr/lib/systemd/system/NetworkManager-dispatcher.service"

# Display manager — vendor greetd, verified by the bootstrap postflight. The
# greeter runs DMS on Hyprland as the generic greeter account.
CopyFile "/etc/greetd/config.toml"
CreateLink "/etc/systemd/system/display-manager.service" "/usr/lib/systemd/system/greetd.service"
