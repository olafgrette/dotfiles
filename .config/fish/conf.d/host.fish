# Use short hostname — personal-hosts and hosts/ dir use short names (olafmbp),
# but uname -n can return FQDN like olafmbp.local on macOS.
set -l _raw_host (hostname -s 2>/dev/null; or uname -n)
set -l _host (string split . $_raw_host)[1]
set -l _host_conf ~/.config/fish/conf.d/hosts/$_host.fish
if test -f $_host_conf
    source $_host_conf
end
