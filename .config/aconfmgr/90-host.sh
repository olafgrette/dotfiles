# Exact hostname overlay dispatch.
#
# Overlays under hosts/ carry no .sh suffix on purpose: aconfmgr auto-sources
# "$config_dir"/*.sh, and host intent must never load on the wrong machine.
# Fails closed — a declared host with no overlay is a configuration error, not
# a reason to converge it against common intent alone.

_aconf_host="$(hostname -s 2>/dev/null || uname -n)"
_aconf_host="${_aconf_host%%.*}"

if [[ -f "$config_dir/hosts/$_aconf_host" ]]
then
	source "$config_dir/hosts/$_aconf_host"
else
	FatalError 'No host overlay for %s in %s\n' \
		"$(Color C "%q" "$_aconf_host")" "$(Color C "%q" "$config_dir/hosts")"
fi

unset _aconf_host
