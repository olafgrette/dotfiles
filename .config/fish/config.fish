fish_add_path ~/bin ~/.local/bin ~/.bun/bin ~/.cargo/bin ~/.opencode/bin

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

if status is-interactive
    printf "\033[5 q"
end

starship init fish | source

# Work and machine settings have final precedence over shared defaults.
if test -f $__fish_config_dir/local.fish
    source $__fish_config_dir/local.fish
end

if status is-interactive
    set -l _bg_cmd 'source $argv[1]; background-startup'
    set -l _bg_source $__fish_config_dir/functions/background-startup.fish
    # setsid is absent on macOS; the child still inherits the final local env.
    if command -q setsid
        setsid fish --no-config -c $_bg_cmd $_bg_source </dev/null >/dev/null 2>&1 &
    else
        fish --no-config -c $_bg_cmd $_bg_source </dev/null >/dev/null 2>&1 &
    end
    disown $last_pid
end
