function skill-sync
    set -l dotfiles (realpath (dirname (realpath (status current-filename)))/../../..)
    set -l skills_src $dotfiles/skills
    # Link skills individually so local and tool-managed skills can coexist.
    set -l skills_dsts ~/.claude/skills ~/.codex/skills ~/.gemini/config/skills

    for skills_dst in $skills_dsts
        mkdir -p $skills_dst
        # Only remove broken links to direct children of this repo's skills.
        for link in $skills_dst/*
            test -L $link; and not test -e $link; or continue
            set -l target (readlink $link); or return 1
            if test (path dirname -- $target) = "$skills_src"
                command rm -- $link; or return 1
            end
        end
        for skill in $skills_src/*/
            ln -sfn $skill $skills_dst/(basename $skill)
        end
    end
end
