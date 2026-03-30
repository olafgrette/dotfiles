if status is-interactive
    fish --no-config -c "source $HOME/.config/fish/functions/background-startup.fish; background-startup" </dev/null >/dev/null 2>&1 &
    disown $last_pid
end
