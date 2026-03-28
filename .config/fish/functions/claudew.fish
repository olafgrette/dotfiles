function claudew
    printf "\033]0;%s\007" $argv[1]
    claude "/rename $argv[1]"
end
