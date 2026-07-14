function background-startup
    # Every new interactive shell (tmux/zellij pane, etc.) spawns this, so
    # skip if it already ran recently to avoid piling up concurrent runs.
    set -l marker /tmp/.dotfiles-background-startup-(id -u)
    set -l cooldown 300
    if test -f $marker
        set -l last (date -r $marker +%s)
        set -l now (date +%s)
        if test (math $now - $last) -lt $cooldown
            return
        end
    end
    touch $marker

    set -l dotfiles (realpath (dirname (realpath (status current-filename)))/../../..)
    if test -d $dotfiles/.git
        git -C $dotfiles pull --ff-only >/dev/null 2>&1
        and bash $dotfiles/install.sh >/dev/null 2>&1
    end

    source $HOME/.config/fish/functions/claude-skill-sync.fish
    claude-skill-sync
    if test -x ~/.local/bin/brunnr
        ~/.local/bin/brunnr update >/dev/null 2>&1
    end
end
