if status is-interactive
    set -l _bg_cmd "source $HOME/.config/fish/functions/background-startup.fish; background-startup"
    # setsid is Linux util-linux, absent on macOS — fall back to plain background
    if type -q setsid
        setsid fish --no-config -c $_bg_cmd </dev/null >/dev/null 2>&1 &
    else
        fish --no-config -c $_bg_cmd </dev/null >/dev/null 2>&1 &
    end
    disown $last_pid
end
