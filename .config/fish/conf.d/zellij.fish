if status is-interactive; and set -q ZELLIJ
    # New tabs default to "Tab #N"; rename to a bare number. Only fires once
    # per tab since the pattern no longer matches after the first rename.
    set -l info (zellij action current-tab-info 2>/dev/null)
    set -l n (string match -r --groups-only 'name: Tab #(\d+)$' -- $info[1])
    if test -n "$n"
        zellij action rename-tab $n 2>/dev/null
    end
end
