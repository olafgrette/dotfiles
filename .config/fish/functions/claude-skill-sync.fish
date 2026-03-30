function claude-skill-sync
    set skills_src ~/dotfiles/.claude/skills
    set skills_dst ~/.claude/skills
    mkdir -p $skills_dst
    for skill in $skills_src/*/
        ln -sfn $skill $skills_dst/(basename $skill)
    end
end
