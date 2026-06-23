function zmux --description 'attach/create persistent zellij session'
    # On Linux, run inside a transient systemd --user scope so the session
    # survives an abrupt SSH disconnect instead of being reaped with the login
    # session's scope (pairs with `loginctl enable-linger`, set up by install.sh).
    if command -q systemd-run
        systemd-run --scope --user zellij attach -c main
    else
        zellij attach -c main
    end
end
