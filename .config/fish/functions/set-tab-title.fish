function set-tab-title
    printf "\033]0;%s\007" $argv[1]
end
