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

    # Resolve the installed symlink, then walk up from .config/fish/functions.
    set -l this_file (path resolve (status current-filename)); or return 1
    set -l dotfiles (path dirname (path dirname (path dirname (path dirname $this_file))))
    if test -d $dotfiles/.git
        git -C $dotfiles pull --ff-only >/dev/null 2>&1
        and bash $dotfiles/install.sh >/dev/null 2>&1
    end

    source $HOME/.config/fish/functions/skill-sync.fish
    skill-sync
    if test -x ~/.local/bin/brunnr
        ~/.local/bin/brunnr update >/dev/null 2>&1
    end
end
