function fish_greeting
    set -l quotes

    # ---- 7cb56ce / 9d8dddb+c1ec3e9 — initial batch
    # Author: Claude <noreply@anthropic.com> — session 01ANEdfsmVDMFSueexKDydSp (2026-03-29)
    # Merged as PR #1 (7cb56ce) by Olaf. Original fish puns.
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

    # ---- 5975a26 — expansion: industry cynicism + eldritch horror (2026-04-01)
    # Author: Olaf Grette (no explicit Co-Authored-By, but same era as Sonnet 4.6)
    # Adds dev-lifecycle puns and Lovecraftian references.
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

    # ---- ecc5835 — final additions (2026-05-30)
    # Author: Olaf Grette — era of Sonnet 4.6 (neighbor commits have Co-Authored-By: Sonnet 4.6)
    # Cthulhu finale + BASH pun.
    set -a quotes \
        "><(((º>  BASH: Barracuda's Alternative Shell." \
        "><(((º>  Iä! Iä! Sudo fhtagn!" \
        "><(((º>  Whale, whale, whale, look who's root."

    # Retired in ecc5835 (kept here as comment for archeology):
    #   Oh shell, you're back.
    #   You've got bigger fish to fry.
    #   git blame? More like git shame.
    #   Current branch: swimming in circles.
    #   You're on a reel today.
    #   Making waves in production again?
    #   Still waiting on code review. Must be the current.
    #   That last commit? Reel questionable.
    #   The deep end of the stack trace awaits.
    #   curl -L life | grep meaning
    #   Sinking into the deep end of the backlog.
    #   The current state of the repo: murky.

    echo $quotes[(random 1 (count $quotes))]
end
