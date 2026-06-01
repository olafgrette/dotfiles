function background-startup
    source $HOME/.config/fish/functions/claude-skill-sync.fish
    claude-skill-sync
    if test -x ~/.local/bin/brunnr
        ~/.local/bin/brunnr update >/dev/null 2>&1
    end
end
