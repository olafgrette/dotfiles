function zmux --description 'attach/create persistent zellij session, detaching stale clients'
    set -l session main
    test (count $argv) -gt 0; and set session $argv[1]

    if set -q ZELLIJ
        echo "zmux: already inside a zellij session" >&2
        return 1
    end

    # Create the session — and with it the long-lived server process — detached,
    # inside a transient systemd --user scope so it survives an abrupt SSH
    # disconnect instead of being reaped with the login session's scope (pairs
    # with `loginctl enable-linger`, set up by install.sh). Only the *server*
    # needs to escape the login scope: wrapping the client too (as this function
    # used to) is what leaves a zombie client attached after the terminal dies.
    # `attach -b` exits 1 with "Session already exists" when it's already up, and
    # resurrects an exited session detached — either way, nothing to do here.
    if command -q systemd-run
        systemd-run --scope --user --quiet --collect zellij attach --create-background $session 2>/dev/null
    else
        zellij attach --create-background $session 2>/dev/null
    end

    # tmux's `new -AD` detaches every other client on attach; zellij has no
    # equivalent, and `action detach` is not a substitute: a CLI action is routed
    # to the session's *last active* client, so it can't reach a client that never
    # took input — precisely the zombies we're here to clear. Ask politely once
    # (this restores the terminal for a live client we're stealing the session
    # from), then drop the rest at the process level, which the server handles as
    # an ordinary disconnect.
    zellij --session $session action detach 2>/dev/null

    # Match the zellij binary by name and the session by argument. Both discriminators
    # are load-bearing: the server is also named `zellij` (excluded via --server),
    # while the shells running *inside* the panes are the processes carrying
    # ZELLIJ_SESSION_NAME — matching on that env var would kill your panes and
    # leave the clients.
    for pid in (pgrep -x zellij 2>/dev/null)
        set -l cmd (ps -p $pid -o args= 2>/dev/null)
        string match -q '*--server*' -- $cmd; and continue
        contains -- $session (string split ' ' -- $cmd); or continue
        kill $pid 2>/dev/null
    end
    sleep 0.2 # let the server reap the disconnects before we attach

    # Foreground and unwrapped, so this client dies with the terminal. `--create`
    # is the fallback for hosts where the scoped creation above couldn't run
    # (containers/WSL with loginctl but no running systemd).
    zellij attach --create $session
end
