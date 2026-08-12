function zmux --description 'attach/create persistent zellij session, detaching stale clients'
    set -l session main

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

    # tmux's `new -AD` detaches every other client on attach; zellij has no such
    # flag. A CLI action is applied to the session's last active client, so kick
    # them off one at a time — `list-clients` prints a header plus one row per
    # attached client, and everything still attached at this point is stale by
    # definition, since we haven't attached yet. Bounded so a client the server
    # refuses to drop can't wedge the loop.
    for attempt in (seq 10)
        set -l clients (zellij --session $session action list-clients 2>/dev/null | string match -rv '^CLIENT_ID')
        test (count $clients) -gt 0; or break
        zellij --session $session action detach 2>/dev/null
    end

    # Foreground and unwrapped, so this client dies with the terminal. `--create`
    # is the fallback for hosts where the scoped creation above couldn't run
    # (containers/WSL with loginctl but no running systemd).
    zellij attach --create $session
end
