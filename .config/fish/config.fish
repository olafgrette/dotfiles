fish_add_path ~/bin ~/.local/bin

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

starship init fish | source
