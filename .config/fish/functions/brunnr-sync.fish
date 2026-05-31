function brunnr-sync
    set -l brunnr_dir $HOME/.cache/brunnr
    if not test -d $brunnr_dir
        git clone --quiet git@github.com:olafgrette/brunnr.git $brunnr_dir
    else
        git -C $brunnr_dir pull --quiet
    end
end
