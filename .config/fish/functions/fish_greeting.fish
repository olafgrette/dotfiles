function fish_greeting
    set -l quotes

    # sonnet 4.6
    set -a quotes \
        "><(((º>  Another day, another fathom." \
        "><(((º>  Scaling up..." \
        "><(((º>  Don't flounder — you've got this." \
        "><(((º>  Gill-ty of opening another terminal." \
        "><(((º>  Just keep committing, just keep committing." \
        "><(((º>  Something smells like a merge conflict." \
        "><(((º>  The upstream is strong today." \
        "><(((º>  Reeling in the dependencies..." \
        "><(((º>  New shell, who dis?" \
        "><(((º>  Spawning a new session..." \
        "><(((º>  The porpoise of this terminal is unclear." \
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
        "><(((º>  \$PATH to the sea." \
        "><(((º>  piping output to /dev/ocean." \
        "><(((º>  0 0 * * *  release the kraken." \
        "><(((º>  /dev/null is where dreams go to swim." \
        "><(((º>  tail -f /var/log/ocean.log" \
        "><(((º>  brew install ambition — already up to date."

    # opus 4.6
    set -a quotes \
        "><(((º>  Don't be koi, show me the diff." \
        "><(((º>  Dockerized or wild-caught?" \
        "><(((º>  SSH: Secret Shell Harbor." \
        "><(((º>  YAML: Yet Another Marine Lifeform." \
        "><(((º>  JSON: Jellyfish Standard Object Notation." \
        "><(((º>  CI/CD: Constant Inundation / Continuous Drowning." \
        "><(((º>  Sustainable code: wild-caught from GitHub." \
        "><(((º>  Data lake? More like data swamp." \
        "><(((º>  In his house at R'lyeh, dead Cthulhu waits dreaming... of a bug-free build." \
        "><(((º>  That is not dead which can eternal lie, and with strange eons even legacy code may die." \
        "><(((º>  The Call of the CLI: madness in every man page." \
        "><(((º>  The Great Old Ones: COBOL, Fortran, and Lisp." \
        "><(((º>  Eldritch errors in the logs. Don't look too close." \
        "><(((º>  Ph'nglui mglw'nafh git commit r'lyeh wgah'nagl fhtagn." \
        "><(((º>  Your shell is a window into the abyss. And the abyss is piping to stderr."

    # opus 4.8
    set -a quotes \
        "><(((º>  BASH: Barracuda's Alternative Shell." \
        "><(((º>  Iä! Iä! Sudo fhtagn!" \
        "><(((º>  Whale, whale, whale, look who's root."

    # muse spark 1.1
    set -a quotes \
        "><(((º>  Carp-et diem — seize the merge window." \
        "><(((º>  Seas the day, ship to prod." \
        "><(((º>  Don't be shellfish, share the cache." \
        "><(((º>  This PR looks a bit fishy — in a good way." \
        "><(((º>  Tuna-ing the GC for better latency." \
        "><(((º>  Betta run tests before you merge." \
        "><(((º>  Cod review: LGTM, let's land it." \
        "><(((º>  Water you waiting for? Commit already." \
        "><(((º>  Shrimply the best refactor I've seen." \
        "><(((º>  Off the hook — zero warnings." \
        "><(((º>  Sardine-packed backlog, still shipping." \
        "><(((º>  Minnow if I told you we fixed it in prod?" \
        "><(((º>  Tide-ally you should rebase now." \
        "><(((º>  The abyss also has a fish shell. It's deeper." \
        "><(((º>  rm -rf /ocean — bold strategy, minnow."

    echo $quotes[(random 1 (count $quotes))]
end
