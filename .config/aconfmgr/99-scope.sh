# Finalize /etc allowlist — fail-closed, runtime-derived.
#
# After common, host and local declarations, ignore every existing /etc path
# except the exact registered managed paths and their ancestor directories.
# This inverts the failure mode from "forgot to exclude X" to "X not included".
# Keep all non-/etc roots excluded via 00-scope.sh; this file only handles /etc.
#
# Registered exact managed paths are currently:
# common:
#   /etc/cron.d/timeshift-hourly
#   /etc/systemd/system/multi-user.target.wants/cronie.service  (enablement)
# Lightshow:
#   /etc/fuse.conf
#   /etc/greetd/config.toml
#   /etc/locale.conf
#   /etc/locale.gen  (one-line en_US.UTF-8)
#   /etc/pacman.conf  (current pacnew with [multilib] enabled)
#   /etc/pacman.d/hooks/nvidia.hook
#   /etc/systemd/system/grub-btrfsd.service.d/override.conf  (ExecStart reset + --timeshift-auto --syslog)
#   /etc/localtime  (symlink to /usr/share/zoneinfo/America/Los_Angeles)
#   /etc/systemd/system/display-manager.service  (symlink to greetd)
#   /etc/systemd/system/multi-user.target.wants/grub-btrfsd.service  (enablement)
#
# Ancestors that must remain traversable:
#   /etc, /etc/greetd, /etc/pacman.d, /etc/pacman.d/hooks,
#   /etc/cron.d, /etc/systemd, /etc/systemd/system,
#   /etc/systemd/system/multi-user.target.wants,
#   /etc/systemd/system/grub-btrfsd.service.d
#
# No other path outside /etc is managed. No tracked product-specific private
# names; network/security state remains in ignored local intent per Safety
# contract 7.

# Build allowlist from registered managed paths plus their ancestors.
# _aconf_managed is populated by wrappers in 00-scope.sh that intercept every
# CopyFile/CopyFileTo/CreateLink/SetFileProperty destination.
_aconf_allow=("/etc")
for _a in "${_aconf_managed[@]}"; do
    # Add the managed path itself.
    _aconf_allow+=("$_a")
    # Add each ancestor up to /etc (e.g., /etc/a/b/c -> /etc/a/b, /etc/a, /etc).
    _p="$_a"
    while [[ "$_p" == /etc/* ]]; do
        _p="${_p%/*}"
        [[ "$_p" == "" ]] && break
        # Avoid duplicates.
        _found=0
        for _e in "${_aconf_allow[@]}"; do [[ "$_e" == "$_p" ]] && _found=1 && break; done
        [[ $_found -eq 0 ]] && _aconf_allow+=("$_p")
        [[ "$_p" == "/etc" ]] && break
    done
done

# Helper: check if path is allowlisted or ancestor of allowlisted.
_aconf_is_allowed() {
    local p="$1" a
    for a in "${_aconf_allow[@]}"; do
        [[ "$p" == "$a" ]] && return 0
        [[ "$a" == "$p"/* ]] && return 0
    done
    return 1
}

# Enumerate existing /etc tree and ignore everything not allowed.
# Use find to list files, dirs and symlinks; ignore the allowlist set.
if [[ -d /etc ]]; then
    while IFS= read -r -d '' _p; do
        if ! _aconf_is_allowed "$_p"; then
            IgnorePath "$_p"
            # For directories, also ignore descendants via glob to prevent
            # aconfmgr's later package-ownership discovery from re-adding
            # modified files under ignored trees.
            if [[ -d "$_p" ]]; then
                IgnorePath "$_p/*"
            fi
        fi
    done < <(find /etc -mindepth 1 -print0 2>/dev/null || true)
fi

# Fail closed. This asserts the safety property itself rather than a proxy for
# it: every sentinel that exists must match aconfmgr's own ignore_paths after
# derivation. A silent find failure, a regression in the allowlist logic, or a
# managed path that widens scope all surface here instead of at the next push.
# The match mirrors aconfmgr's own test at common.bash:500 (unquoted glob).
# Sentinels are leaf paths that must never be published, chosen so that no
# legitimate future allowlist entry can trip them.
for _p in /etc/shadow /etc/gshadow /etc/passwd /etc/group \
	/etc/fstab /etc/crypttab /etc/hostname /etc/machine-id \
	/etc/sudoers /etc/sudoers.d /etc/ssh/sshd_config \
	/etc/ssh/ssh_host_ed25519_key /etc/ssh/ssh_host_rsa_key \
	/etc/ssh/ssh_host_ecdsa_key /etc/NetworkManager/system-connections
do
	[[ -e "$_p" ]] || continue
	_found=0
	for _a in "${ignore_paths[@]}"
	do
		# shellcheck disable=SC2053  # glob match is intentional
		if [[ "$_p" == $_a ]]
		then
			_found=1
			break
		fi
	done
	(( _found )) || FatalError \
		'Scope check failed: %s is not ignored. Refusing to continue.\n' \
		"$(Color C "%q" "$_p")"
done

unset _aconf_allow
unset -f _aconf_is_allowed
unset _p _a _found
