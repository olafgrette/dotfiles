# Run before conf.d/local.fish can be sourced. Moving it out of conf.d lets
# config.fish load local settings exactly once, after all shared defaults.
set -l legacy $__fish_config_dir/conf.d/local.fish
set -l override $__fish_config_dir/local.fish
if test -e $legacy; or test -L $legacy
    if test -e $override; or test -L $override
        echo 'fish: both conf.d/local.fish and local.fish exist; merge them into local.fish. Both files were preserved.' >&2
    else if test -L $legacy
        # Relative links must keep pointing at the same private file after moving.
        set -l target (path resolve $legacy); or return 1
        command ln -s -- $target $override
        and command rm -- $legacy
    else
        command mv -n -- $legacy $override
    end
end
