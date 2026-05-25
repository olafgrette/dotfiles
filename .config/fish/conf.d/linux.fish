if test (uname) != Linux
    exit
end

if not set -q SSH_CONNECTION
    alias open xdg-open
    alias monitor-desk "cp ~/.config/hypr/monitors.lua.desk ~/.config/hypr/monitors.lua && hyprctl reload"
    alias monitor-tv "cp ~/.config/hypr/monitors.lua.tv ~/.config/hypr/monitors.lua && hyprctl reload"

    # Auto-start Hyprland on tty1
    if not set -q DISPLAY; and test "$XDG_VTNR" = 1
        mkdir -p ~/.cache
        exec start-hyprland > ~/.cache/hyprland.log 2>&1
    end
end
