# Finalize /etc allowlist — fail-closed, runtime-derived.
#
# Ignore existing and package-owned /etc paths except registered destinations
# and their ancestors. Package inventories also cover deleted files: aconfmgr
# otherwise treats their absence as drift and offers to restore them.

# _aconf_managed is populated by wrappers in 00-scope.sh that intercept every
# CopyFile/CopyFileTo/CreateLink/SetFileProperty destination.
_aconf_allow=("/etc" "${_aconf_managed[@]}")

_aconf_is_allowed() {
    local p="$1" a
    for a in "${_aconf_allow[@]}"; do
        [[ "$p" == "$a" ]] && return 0
        [[ "$a" == "$p"/* ]] && return 0
    done
    return 1
}

_aconf_collect_scope() {
    local owned candidates p
    local descend=()
    if ! owned=$("${PACMAN:-pacman}" --query --list --quiet); then
        FatalError 'Cannot enumerate package-owned paths; refusing to derive scope.\n'
        return 1
    fi
    # Only descend into declared ancestors. Unmanaged directories are ignored
    # as a whole, so inspecting their private contents is unnecessary.
    for p in "${_aconf_managed[@]}"; do
        while [[ "$p" == /etc/* ]]; do
            p=${p%/*}
            descend+=(-path "$p" -o)
        done
    done
    candidates=$(mktemp) || return 1
    if ! find /etc -mindepth 1 -print0 -type d ! \( "${descend[@]}" -false \) -prune > "$candidates"; then
        rm -f "$candidates"
        FatalError 'Cannot enumerate managed /etc ancestors; refusing to derive scope.\n'
        return 1
    fi
    while IFS= read -r p; do
        [[ "$p" == /etc/* ]] && printf '%s\0' "${p%/}" >> "$candidates"
    done <<< "$owned"
    while IFS= read -r -d '' p; do
        if ! _aconf_is_allowed "$p"; then
            IgnorePath "$p"
            # Include descendants even when a package directory is absent.
            IgnorePath "$p/*"
        fi
    done < "$candidates"
    rm -f "$candidates"
}
_aconf_collect_scope

# Verify sensitive sentinels against aconfmgr's derived ignore patterns.
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
		# shellcheck disable=SC2053 -- match aconfmgr's unquoted glob test
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
unset -f _aconf_is_allowed _aconf_collect_scope
unset _p _a _found
