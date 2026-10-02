function __zmux_start --argument-names session
    # Create the session — and with it the long-lived server process — detached,
    # inside a transient systemd --user scope so it survives an abrupt SSH
    # disconnect instead of being reaped with the login session's scope (pairs
    # with `loginctl enable-linger`, set up by install.sh). Only the *server*
    # needs to escape the login scope: wrapping the client too (as this function
    # used to) is what leaves a zombie client attached after the terminal dies.
    # Exits non-zero when the session is already up, which callers ignore.
    if command -q systemd-run; and command -q systemctl; and systemctl --user show-environment >/dev/null 2>&1
        systemd-run --scope --user --quiet --collect zellij attach --create-background $session
        and return 0
    end
    # The binary can exist without a reachable user manager (containers/WSL).
    # A failed scoped start can also race manager shutdown; try direct creation.
    zellij attach --create-background $session
end

function __zmux_running --argument-names session
    # `list-sessions` reports resurrectable (exited) sessions alongside live ones;
    # only the absence of the EXITED marker means a server is actually up.
    for line in (zellij list-sessions --no-formatting 2>/dev/null)
        test (string split -m1 -f1 ' ' -- $line) = "$session"; or continue
        string match -q '*(EXITED*' -- $line; and return 1
        return 0
    end
    return 1
end

function __zmux_exited --argument-names session
    for line in (zellij list-sessions --no-formatting 2>/dev/null)
        test (string split -m1 -f1 ' ' -- $line) = "$session"; or continue
        string match -q '*(EXITED*' -- $line
        return $status
    end
    return 1
end

function __zmux_ensure --argument-names session
    __zmux_running $session; and return 0
    __zmux_start $session; or return 1
    set -l attempts 0
    while test $attempts -lt 20
        if __zmux_running $session
            # A plugin-only saved layout briefly accepts connections before
            # exiting. A socket response alone does not mean startup succeeded.
            sleep 0.5
            __zmux_running $session
            return $status
        end
        sleep 0.1
        set attempts (math $attempts + 1)
    end
    return 1
end

function zmux --description 'attach/create persistent zellij session, detaching stale clients'
    # Default to the box's hostname rather than a fixed "main": zellij's
    # tab-bar plugin shows the session name up top, so this is what puts the
    # hostname in the header bar — natively, no status-bar plugin needed.
    # Truncated at the first '.' to keep fully qualified hosts
    # (e.g. "build-42.example.com") from producing an unwieldy session name.
    set -l session (uname -n | string replace -r -- '[.].*' '')
    test (count $argv) -gt 0; and set session $argv[1]

    if set -q ZELLIJ
        echo "zmux: already inside a zellij session" >&2
        return 1
    end

    if not __zmux_ensure $session
        if not __zmux_exited $session
            echo "zmux: could not start session '$session'; saved session retained" >&2
            return 1
        end
        # A failed resurrection is disposable. Never force deletion: another
        # client may have started this session since the exited-state check.
        echo "zmux: clearing failed saved session '$session' and starting fresh" >&2
        zellij delete-session $session >/dev/null; or return 1
        __zmux_ensure $session; or begin
            echo "zmux: could not start fresh session '$session'" >&2
            return 1
        end
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

    # Foreground and unwrapped, so this client dies with the terminal. --create
    # covers a server exiting between readiness and this attach.
    zellij attach --create $session
end
