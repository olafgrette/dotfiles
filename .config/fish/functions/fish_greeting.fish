function fish_greeting
    set -l quotes \
        "><(((º>  Oh shell, you're back." \
        "><(((º>  Another day, another fathom." \
        "><(((º>  Scaling up..." \
        "><(((º>  You've got bigger fish to fry." \
        "><(((º>  Don't flounder — you've got this." \
        "><(((º>  Gill-ty of opening another terminal." \
        "><(((º>  Just keep committing, just keep committing." \
        "><(((º>  Something smells like a merge conflict." \
        "><(((º>  The upstream is strong today." \
        "><(((º>  Reeling in the dependencies..." \
        "><(((º>  git blame? More like git shame." \
        "><(((º>  New shell, who dis?" \
        "><(((º>  Spawning a new session..." \
        "><(((º>  Current branch: swimming in circles." \
        "><(((º>  The porpoise of this terminal is unclear." \
        "><(((º>  You're on a reel today." \
        "><(((º>  Making waves in production again?" \
        "><(((º>  Still waiting on code review. Must be the current." \
        "><(((º>  That last commit? Reel questionable." \
        "><(((º>  Angling for a solution." \
        "><(((º>  Treading water until the tests pass." \
        "><(((º>  hooks? we got hooks." \
        "><(((º>  Trawling through Stack Overflow again." \
        "><(((º>  Gone fishing... in the logs." \
        "><(((º>  Swimming upstream with a hotfix." \
        "><(((º>  Hooked another dependency." \
        "><(((º>  Wading into legacy code again." \
        "><(((º>  Sole survivor of the last deploy." \
        "><(((º>  You can't kelp yourself, can you." \
        "><(((º>  Baited by another bug report." \
        "><(((º>  Net positive changes today? Let's see." \
        "><(((º>  Forking around again." \
        "><(((º>  Caught between a reef and a hard place." \
        "><(((º>  The deep end of the stack trace awaits." \
        "><(((º>  \$PATH to the sea." \
        "><(((º>  piping output to /dev/ocean." \
        "><(((º>  0 0 * * *  release the kraken." \
        "><(((º>  /dev/null is where dreams go to swim." \
        "><(((º>  tail -f /var/log/ocean.log" \
        "><(((º>  curl -L life | grep meaning" \
        "><(((º>  brew install ambition — already up to date." \
        "><(((º>  Don't be koi, show me the diff." \
        "><(((º>  Dockerized or wild-caught?" \
        "><(((º>  SSH: Secret Shell Harbor." \
        "><(((º>  YAML: Yet Another Marine Lifeform." \
        "><(((º>  JSON: Jellyfish Standard Object Notation." \
        "><(((º>  CI/CD: Constant Inundation / Continuous Drowning." \
        "><(((º>  Sustainable code: wild-caught from GitHub." \
        "><(((º>  Sinking into the deep end of the backlog." \
        "><(((º>  Data lake? More like data swamp." \
        "><(((º>  The current state of the repo: murky." \
        "><(((º>  In his house at R'lyeh, dead Cthulhu waits dreaming... of a bug-free build." \
        "><(((º>  That is not dead which can eternal lie, and with strange eons even legacy code may die." \
        "><(((º>  The Call of the CLI: madness in every man page." \
        "><(((º>  The Great Old Ones: COBOL, Fortran, and Lisp." \
        "><(((º>  Eldritch errors in the logs. Don't look too close." \
        "><(((º>  Ph'nglui mglw'nafh git commit r'lyeh wgah'nagl fhtagn." \
        "><(((º>  Your shell is a window into the abyss. And the abyss is piping to stderr."
    echo $quotes[(random 1 (count $quotes))]
end
