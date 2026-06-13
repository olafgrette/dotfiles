if test (uname) != Linux
    exit
end

if not set -q SSH_CONNECTION
    alias open xdg-open
end
