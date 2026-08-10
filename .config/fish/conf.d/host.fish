# Use short hostname — personal-hosts and hosts/ dir use short names (olafmbp),
# but uname -n can return FQDN like olafmbp.local on macOS, hence the split.
# uname is coreutils (always present); hostname is not (inetutils, optional on Arch).
set -l _host (string split . (uname -n))[1]
set -l _host_conf ~/.config/fish/conf.d/hosts/$_host.fish
if test -f $_host_conf
    source $_host_conf
end
