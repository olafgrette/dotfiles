set -l _host_conf ~/.config/fish/conf.d/hosts/(uname -n).fish
if test -f $_host_conf
    source $_host_conf
end
