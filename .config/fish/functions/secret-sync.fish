function __secret_sync_mode --argument-names target
    if test (uname) = Darwin
        stat -f '%Lp' $target 2>/dev/null
    else
        stat -c '%a' $target 2>/dev/null
    end
end

function __secret_sync_install --argument-names source target mode
    set -l parent (path dirname $target)
    command mkdir -p $parent; or return 1
    if test (path basename $parent) = .ssh
        command chmod 700 $parent; or return 1
    end

    set -l temporary (command mktemp "$parent/."(path basename $target)".secret-sync.XXXXXX"); or return 1
    command cp $source $temporary
    and command chmod $mode $temporary
    and command mv -f $temporary $target
    set -l result $status
    if test -e $temporary
        command rm -f $temporary
    end
    return $result
end

function __secret_sync_rclone_update --argument-names source client_id client_secret output
    set -l in_gdrive 0
    set -l found_gdrive 0
    set -l seen_client_id 0
    set -l seen_client_secret 0

    while read -l line
        if string match -rq '^\s*\[[^]]+\]\s*$' -- $line
            if test $in_gdrive -eq 1
                if test $seen_client_id -eq 0
                    printf 'client_id = %s\n' $client_id
                end
                if test $seen_client_secret -eq 0
                    printf 'client_secret = %s\n' $client_secret
                end
                set in_gdrive 0
            end
            if test (string trim -- $line) = '[gdrive]'
                set in_gdrive 1
                set found_gdrive 1
            end
            printf '%s\n' $line
            continue
        end

        if test $in_gdrive -eq 1
            if string match -rq '^\s*client_id\s*=' -- $line
                if test $seen_client_id -eq 0
                    printf 'client_id = %s\n' $client_id
                    set seen_client_id 1
                end
                continue
            else if string match -rq '^\s*client_secret\s*=' -- $line
                if test $seen_client_secret -eq 0
                    printf 'client_secret = %s\n' $client_secret
                    set seen_client_secret 1
                end
                continue
            end
        end
        printf '%s\n' $line
    end <$source >$output

    if test $in_gdrive -eq 1
        if test $seen_client_id -eq 0
            printf 'client_id = %s\n' $client_id >>$output
        end
        if test $seen_client_secret -eq 0
            printf 'client_secret = %s\n' $client_secret >>$output
        end
    end
    if test $found_gdrive -eq 0
        echo "secret-sync: rclone remote 'gdrive' does not exist; create it with 'rclone config' first" >&2
        return 1
    end
end

function __secret_sync_pull --argument-names temporary assume_yes
    # Bitwarden item IDs are identifiers, not credentials. The item schemas and
    # local destinations are intentionally fixed rather than configurable.
    set -l ssh_item_id 0bafc73b-6cb2-422a-84bf-b31a013a615
    set -l gdrive_item_id 5ab3744e-48e9-4343-8e68-b4ae009a0d36

    bw sync >/dev/null; or begin
        echo 'secret-sync: Bitwarden sync failed' >&2
        return 1
    end
    bw get item $ssh_item_id >"$temporary/ssh.json"; or begin
        echo "secret-sync: could not fetch SSH item $ssh_item_id" >&2
        return 1
    end
    bw get item $gdrive_item_id >"$temporary/gdrive.json"; or begin
        echo "secret-sync: could not fetch Google OAuth item $gdrive_item_id" >&2
        return 1
    end

    set -l private "$temporary/id_ed25519"
    set -l public "$temporary/id_ed25519.pub"
    set -l derived "$temporary/id_ed25519.derived"
    jq -je '.type == 5 and (.sshKey.privateKey | type == "string" and length > 0)' "$temporary/ssh.json" >/dev/null
    and jq -jer '.sshKey.privateKey | sub("\n+$"; "") + "\n"' "$temporary/ssh.json" >$private
    or begin
        echo "secret-sync: item $ssh_item_id is not an SSH Key with a privateKey" >&2
        return 1
    end
    jq -jer '.sshKey.publicKey | select(type == "string" and length > 0) | sub("\n+$"; "") + "\n"' "$temporary/ssh.json" >$public; or begin
        echo "secret-sync: item $ssh_item_id has no publicKey" >&2
        return 1
    end
    command chmod 600 $private $public
    ssh-keygen -y -f $private >$derived; or begin
        echo "secret-sync: ssh-keygen could not derive the public key for item $ssh_item_id" >&2
        return 1
    end

    set -l stored_parts (string split ' ' -- (string trim < $public))
    set -l derived_parts (string split ' ' -- (string trim < $derived))
    if test (count $stored_parts) -lt 2; or test (count $derived_parts) -lt 2
        echo "secret-sync: invalid public key in item $ssh_item_id" >&2
        return 1
    end
    if test $stored_parts[1] != $derived_parts[1]; or test $stored_parts[2] != $derived_parts[2]
        echo "secret-sync: private/public key mismatch in item $ssh_item_id" >&2
        return 1
    end
    printf '%s %s %s\n' $stored_parts[1] $stored_parts[2] olaf@grette.org >$public
    set -l fingerprint_parts (string split ' ' -- (ssh-keygen -lf $public)); or return 1
    set -l fingerprint $fingerprint_parts[2]
    set -l expected_fingerprint (jq -r '.sshKey.keyFingerprint // .sshKey.fingerprint // empty' "$temporary/ssh.json")
    if test -n "$expected_fingerprint"; and test "$expected_fingerprint" != "$fingerprint"
        echo "secret-sync: stored SSH fingerprint mismatch: expected $expected_fingerprint, derived $fingerprint" >&2
        return 1
    end

    set -l client_id (jq -er '.login.username | select(type == "string" and length > 0 and (contains("\n") | not) and (contains("\r") | not))' "$temporary/gdrive.json" | string collect); or begin
        echo "secret-sync: item $gdrive_item_id has no valid login.username for client_id" >&2
        return 1
    end
    set -l client_secret (jq -er '.login.password | select(type == "string" and length > 0 and (contains("\n") | not) and (contains("\r") | not))' "$temporary/gdrive.json" | string collect); or begin
        echo "secret-sync: item $gdrive_item_id has no valid login.password for client_secret" >&2
        return 1
    end

    set -l rclone_config
    if set -q XDG_CONFIG_HOME
        set rclone_config "$XDG_CONFIG_HOME/rclone/rclone.conf"
    else
        set rclone_config "$HOME/.config/rclone/rclone.conf"
    end
    if test "$rclone_config" != "$HOME"; and not string match -q "$HOME/*" -- $rclone_config
        echo 'secret-sync: XDG_CONFIG_HOME must be inside HOME' >&2
        return 1
    end
    if test -L $rclone_config; or not test -f $rclone_config
        echo "secret-sync: rclone config must be an existing regular file: $rclone_config" >&2
        return 1
    end
    if test -L "$HOME/.ssh"
        echo "secret-sync: refusing SSH materialization through symlink: $HOME/.ssh" >&2
        return 1
    end
    for target in "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_ed25519.pub"
        if test -L $target; or begin
                test -e $target; and not test -f $target
            end
            echo "secret-sync: refusing non-regular SSH destination: $target" >&2
            return 1
        end
    end

    set -l rclone_output "$temporary/rclone.conf"
    __secret_sync_rclone_update $rclone_config $client_id $client_secret $rclone_output; or return 1

    set -l sources $private $public $rclone_output
    set -l targets "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_ed25519.pub" $rclone_config
    set -l modes 600 644 600
    set -l descriptions "SSH private key ($fingerprint)" "SSH public key ($fingerprint)" 'rclone OAuth client for gdrive'
    set -l changed
    set -l index 1
    while test $index -le (count $sources)
        if not test -f $targets[$index]
            set -a changed $index
        else if not command cmp -s $sources[$index] $targets[$index]
            set -a changed $index
        else if test (__secret_sync_mode $targets[$index]) != $modes[$index]
            set -a changed $index
        else if test (path basename (path dirname $targets[$index])) = .ssh; and test (__secret_sync_mode (path dirname $targets[$index])) != 700
            set -a changed $index
        end
        set index (math $index + 1)
    end

    if test (count $changed) -eq 0
        echo 'Secrets already match Bitwarden.'
        return 0
    end

    echo 'Planned secret updates:'
    for index in $changed
        printf '  %s (%s, mode %s)\n' $targets[$index] $descriptions[$index] $modes[$index]
    end
    if test $assume_yes -ne 1
        read -l -P 'Apply these updates? [y/N] ' answer; or set answer ''
        if not contains -- (string lower (string trim -- $answer)) y yes
            echo 'secret-sync: secret sync cancelled' >&2
            return 2
        end
    end

    for index in $changed
        __secret_sync_install $sources[$index] $targets[$index] $modes[$index]; or begin
            echo "secret-sync: failed to install $targets[$index]" >&2
            return 1
        end
    end
    echo "Applied "(count $changed)" secret update(s)."
end

function secret-sync --description 'manually materialize personal secrets from Bitwarden'
    if test (count $argv) -lt 1; or test $argv[1] != pull
        echo 'usage: secret-sync pull [--yes]' >&2
        return 2
    end
    set -l assume_yes 0
    for argument in $argv[2..-1]
        if test $argument = --yes
            set assume_yes 1
        else
            echo "secret-sync: unknown argument: $argument" >&2
            return 2
        end
    end
    for command_name in bw jq ssh-keygen mktemp
        if not type -q $command_name
            echo "secret-sync: required command not found: $command_name" >&2
            return 2
        end
    end

    set -l session (env -u BW_SESSION bw unlock --raw | string collect)
    set -l unlock_status $pipestatus[1]
    set session (string trim -- $session)
    if test $unlock_status -ne 0; or test -z "$session"
        echo 'secret-sync: Bitwarden unlock failed; run `bw login` first if needed' >&2
        return 2
    end
    set -lx BW_SESSION $session

    set -l temporary_root /tmp
    if set -q TMPDIR
        set temporary_root $TMPDIR
    end
    set -l temporary (command mktemp -d "$temporary_root/secret-sync.XXXXXX")
    set -l result 1
    if test -n "$temporary"; and test -d $temporary
        __secret_sync_pull $temporary $assume_yes
        set result $status
        if test $result -ne 0
            set result 2
        end
        command rm -rf $temporary
    else
        echo 'secret-sync: could not create a private temporary directory' >&2
    end

    bw lock >/dev/null
    set -l lock_status $status
    set -e BW_SESSION
    if test $lock_status -ne 0
        echo 'secret-sync: `bw lock` failed' >&2
        return 2
    end
    return $result
end
