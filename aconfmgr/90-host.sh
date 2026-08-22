# Exact hostname overlay dispatch.
#
# Overlays under hosts/ carry no .sh suffix on purpose: aconfmgr auto-sources
# "$config_dir"/*.sh, and host intent must never load on the wrong machine.
#
# A declared host with no overlay converges against common intent alone and
# warns. A fresh machine has to be able to bootstrap before anyone has written
# its host file; the warning is the reminder to write one. Host membership is
# still gated — aconf.sh refuses any host absent from personal-hosts.

_aconf_host="$(hostname -s 2>/dev/null || uname -n)"
_aconf_host="${_aconf_host%%.*}"

if [[ -f "$config_dir/hosts/$_aconf_host" ]]
then
	source "$config_dir/hosts/$_aconf_host"
else
	ConfigWarning 'No host overlay for %s; converging against common intent alone.\n' \
		"$(Color C "%q" "$_aconf_host")"
fi

unset _aconf_host
