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

    # Portable dotfiles root — fish's `path resolve` works on both macOS and
    # Linux, unlike `realpath` (BSD vs GNU) and avoids BSD `setsid` issues.
    # `status current-filename` may be a symlink (installed via install.sh),
    # so resolve it then walk up 4 levels: .../functions/background-startup.fish
    # -> functions -> fish -> .config -> dotfiles
    set -l this_file (status current-filename)
    if type -q path
        set -l resolved (path resolve $this_file 2>/dev/null)
        if test -n "$resolved"
            set this_file $resolved
        end
        set -l dotfiles (path dirname (path dirname (path dirname (path dirname $this_file))))
    else
        # Fallback for older fish without `path` builtin
        if type -q realpath
            set -l resolved (realpath $this_file 2>/dev/null)
            if test -n "$resolved"
                set this_file $resolved
            end
        end
        set -l dotfiles (dirname (dirname (dirname (dirname $this_file))))
    end
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
