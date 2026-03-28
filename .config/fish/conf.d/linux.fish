if test (uname) != Linux
    exit
end

# xdg-open shorthand
alias open xdg-open

# Hyprland monitor profiles
alias monitor-desk "cp ~/.config/hypr/monitors.conf.desk ~/.config/hypr/monitors.conf && hyprctl reload"
alias monitor-tv "cp ~/.config/hypr/monitors.conf.tv ~/.config/hypr/monitors.conf && hyprctl reload"

if not set -q SSH_CONNECTION
    # ssh-agent: reuse existing agent or start a new one
    set -l _ssh_env ~/.ssh/environment-$hostname
    if test -f $_ssh_env
        source $_ssh_env > /dev/null
        if not test -S "$SSH_AUTH_SOCK"
            ssh-agent | grep -v '^echo' > $_ssh_env
            chmod 600 $_ssh_env
            source $_ssh_env > /dev/null
        end
    else
        ssh-agent | grep -v '^echo' > $_ssh_env
        chmod 600 $_ssh_env
        source $_ssh_env > /dev/null
    end
    ssh-add -q 2>/dev/null

    # Auto-start Hyprland on tty1
    if not set -q DISPLAY; and test "$XDG_VTNR" = 1
        mkdir -p ~/.cache
        exec start-hyprland > ~/.cache/hyprland.log 2>&1
    end
end
