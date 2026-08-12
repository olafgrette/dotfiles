function host-ssh-agent --description 'wire up a local ssh-agent socket; opt-in per host, not all Linux hosts use one'
    # A forwarded agent (ssh -A) arrives as an already-set SSH_AUTH_SOCK; don't
    # clobber it with the local one.
    # -gx, not -x: a bare `set` inside a function is function-scoped and would
    # vanish on return, leaving the shell with no SSH_AUTH_SOCK.
    if not set -q SSH_AUTH_SOCK
        set -gx SSH_AUTH_SOCK $XDG_RUNTIME_DIR/ssh-agent.socket
    end
    # Only load keys on a local login — a remote one can't answer a passphrase prompt.
    if not set -q SSH_CONNECTION
        if not ssh-add -l >/dev/null 2>&1
            ssh-add ~/.ssh/id_ed25519
        end
    end
end
