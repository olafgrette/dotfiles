fish_add_path ~/bin ~/.local/bin ~/.bun/bin

if command -q hx
    set -x EDITOR hx
    if not command -q helix
        alias helix hx
    end
else if command -q helix
    set -x EDITOR helix
    alias hx helix
end


set -x npm_config_prefix ~/.local

alias mux 'tmux new -AD -s main'
alias brunnr-init '$HOME/.cache/brunnr/bin/brunnr-init'

if status is-interactive
    printf "\033[5 q"
end

starship init fish | source
