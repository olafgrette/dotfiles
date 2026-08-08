function skill-sync
    set -l dotfiles (realpath (dirname (realpath (status current-filename)))/../../..)
    set -l skills_src $dotfiles/skills
    # Link skills individually so local and tool-managed skills can coexist.
    set -l skills_dsts ~/.claude/skills ~/.codex/skills

    for skills_dst in $skills_dsts
        mkdir -p $skills_dst
        for skill in $skills_src/*/
            ln -sfn $skill $skills_dst/(basename $skill)
        end
    end
end
