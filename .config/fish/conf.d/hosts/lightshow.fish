set -x SSH_AUTH_SOCK $XDG_RUNTIME_DIR/ssh-agent.socket

if not ssh-add -l >/dev/null 2>&1
    ssh-add ~/.ssh/id_ed25519
end
