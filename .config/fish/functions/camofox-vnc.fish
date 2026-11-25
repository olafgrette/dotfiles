function camofox-vnc --description "Tunnel to the Camofox noVNC on vps.oag.sh and open it"
    set -l port 6080
    if test (count $argv) -ge 1
        set port $argv[1]
    end

    # Start the tunnel only if nothing is already listening on the local port
    if not ss -tln 2>/dev/null | grep -q ":$port "
        # Bypass Ghostty's SSH wrapper: its terminfo setup also binds forwarded ports.
        command ssh -f -N -o ExitOnForwardFailure=yes -L $port:127.0.0.1:6080 ubuntu@vps.oag.sh
        or return 1
        sleep 1
    end

    xdg-open http://127.0.0.1:$port/vnc.html
end
