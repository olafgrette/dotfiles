function background-startup
    # Resolve the installed symlink, then walk up from .config/fish/functions.
    set -l this_file (path resolve (status current-filename)); or return 1
    set -l dotfiles (path dirname (path dirname (path dirname (path dirname $this_file))))
    python3 $dotfiles/.local/bin/dotfiles-update
end
