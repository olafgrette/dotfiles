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

# Display manager — vendor greetd, verified by the bootstrap postflight. The
# greeter runs DMS on Hyprland as the generic greeter account.
CopyFile "/etc/greetd/config.toml"
CreateLink "/etc/systemd/system/display-manager.service" "/usr/lib/systemd/system/greetd.service"
