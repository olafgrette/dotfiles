function fish_greeting --description "Random ocean-themed greeting"
    set -l fish "><(((º>"

    set -l quotes \
        # sonnet 4.6
        "Another day, another fathom." \
        "Scaling up..." \
        "Don't flounder — you've got this." \
        "Gill-ty of opening another terminal." \
        "Just keep committing, just keep committing." \
        "Something smells like a merge conflict." \
        "The upstream is strong today." \
        "Reeling in the dependencies..." \
        "New shell, who dis?" \
        "Spawning a new session..." \
        "The porpoise of this terminal is unclear." \
        "Angling for a solution." \
        "Treading water until the tests pass." \
        "hooks? we got hooks." \
        "Trawling through Stack Overflow again." \
        "Gone fishing... in the logs." \
        "Swimming upstream with a hotfix." \
        "Hooked another dependency." \
        "Wading into legacy code again." \
        "Sole survivor of the last deploy." \
        "You can't kelp yourself, can you." \
        "Baited by another bug report." \
        "Net positive changes today? Let's see." \
        "Forking around again." \
        "Caught between a reef and a hard place." \
        "\$PATH to the sea." \
        "piping output to /dev/ocean." \
        "0 0 * * *  release the kraken." \
        "/dev/null is where dreams go to swim." \
        "tail -f /var/log/ocean.log" \
        "brew install ambition — already up to date." \
        # opus 4.6
        "Don't be koi, show me the diff." \
        "Dockerized or wild-caught?" \
        "SSH: Secret Shell Harbor." \
        "YAML: Yet Another Marine Lifeform." \
        "JSON: Jellyfish Standard Object Notation." \
        "CI/CD: Constant Inundation / Continuous Drowning." \
        "Sustainable code: wild-caught from GitHub." \
        "Data lake? More like data swamp." \
        "In his house at R'lyeh, dead Cthulhu waits dreaming... of a bug-free build." \
        "That is not dead which can eternal lie, and with strange eons even legacy code may die." \
        "The Call of the CLI: madness in every man page." \
        "The Great Old Ones: COBOL, Fortran, and Lisp." \
        "Eldritch errors in the logs. Don't look too close." \
        "Ph'nglui mglw'nafh git commit r'lyeh wgah'nagl fhtagn." \
        "Your shell is a window into the abyss. And the abyss is piping to stderr." \
        # opus 4.8
        "BASH: Barracuda's Alternative Shell." \
        "Iä! Iä! Sudo fhtagn!" \
        "Whale, whale, whale, look who's root." \
        # muse spark 1.1
        "Carp-et diem — seize the merge window." \
        "Seas the day, ship to prod." \
        "Don't be shellfish, share the cache." \
        "This PR looks a bit fishy — in a good way." \
        "Tuna-ing the GC for better latency." \
        "Betta run tests before you merge." \
        "Cod review: LGTM, let's land it." \
        "Water you waiting for? Commit already." \
        "Shrimply the best refactor I've seen." \
        "Off the hook — zero warnings." \
        "Sardine-packed backlog, still shipping." \
        "Minnow if I told you we fixed it in prod?" \
        "Tide-ally you should rebase now." \
        "The abyss also has a fish shell. It's deeper." \
        "rm -rf /ocean — bold strategy, minnow."

    set -l pick (random choice $quotes)
    echo "$fish  $pick"
end
