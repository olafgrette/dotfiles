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
        "><(((º>  The deep end of the stack trace awaits."
    echo $quotes[(random 1 (count $quotes))]
end
