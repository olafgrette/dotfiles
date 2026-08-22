# Finalize /etc allowlist — fail-closed, runtime-derived.
#
# Ignore every existing /etc path except registered destinations and their
# ancestors. Other roots are excluded by 00-scope.sh.

# _aconf_managed is populated by wrappers in 00-scope.sh that intercept every
# CopyFile/CopyFileTo/CreateLink/SetFileProperty destination.
_aconf_allow=("/etc")
for _a in "${_aconf_managed[@]}"; do
    _aconf_allow+=("$_a")
    _p="$_a"
    while [[ "$_p" == /etc/* ]]; do
        _p="${_p%/*}"
        [[ "$_p" == "" ]] && break
        _found=0
        for _e in "${_aconf_allow[@]}"; do [[ "$_e" == "$_p" ]] && _found=1 && break; done
        [[ $_found -eq 0 ]] && _aconf_allow+=("$_p")
        [[ "$_p" == "/etc" ]] && break
    done
done

_aconf_is_allowed() {
    local p="$1" a
    for a in "${_aconf_allow[@]}"; do
        [[ "$p" == "$a" ]] && return 0
        [[ "$a" == "$p"/* ]] && return 0
    done
    return 1
}

if [[ -d /etc ]]; then
    while IFS= read -r -d '' _p; do
        if ! _aconf_is_allowed "$_p"; then
            IgnorePath "$_p"
            # Prevent package-ownership discovery from re-adding descendants.
            if [[ -d "$_p" ]]; then
                IgnorePath "$_p/*"
            fi
        fi
    done < <(find /etc -mindepth 1 -print0 2>/dev/null || true)
fi

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
unset -f _aconf_is_allowed
unset _p _a _found
