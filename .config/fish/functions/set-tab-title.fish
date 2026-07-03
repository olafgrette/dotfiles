function set-tab-title
    # Under zellij, OSC 0 only renames the pane, not the tab bar label.
    if set -q ZELLIJ
        zellij action rename-tab $argv[1]
    else
        printf "\033]0;%s\007" $argv[1]
    end
end
