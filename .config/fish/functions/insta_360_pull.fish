function insta_360_pull --description 'Copy Insta360 recordings and proxies into dated folders'
    argparse --max-args 0 h/help n/dry-run s/source= d/destination= -- $argv; or return 2
    if set -q _flag_help
        printf '%s\n' \
            'Usage: insta_360_pull [--dry-run] [--source MOUNT] [--destination DIR]' \
            'Copies VID .insv files and paired LRV .lrv files. Never deletes source files.' \
            'Folders use YYYY-MM-DDTHH-MM from the camera filename (no timezone conversion).' \
            'Existing files with the same name and size are skipped (no content check).' \
            'Stop recording before running.'
        return 0
    end

    set -l source /run/media/olaf/6431-3832
    set -l destination ~/gdrive/insta360_raws
    set -q _flag_source; and set source $_flag_source
    set -q _flag_destination; and set destination $_flag_destination
    printf 'Scanning camera: %s\n' "$source"
    if not test -d "$source/DCIM"
        printf 'Camera DCIM directory not found: %s\n' "$source/DCIM" >&2
        return 1
    end
    # Resolve relative destinations before constructing recording paths.
    set destination (path resolve -- "$destination"); or return 1
    set -l files "$source"/DCIM/**/*.insv "$source"/DCIM/**/*.lrv
    if test (count $files) -eq 0
        echo 'No .insv or .lrv files found.' >&2
        return 1
    end

    set -l targets
    set -l recordings
    printf 'Checking recording pairs (%d files)...\n' (count $files)
    # Check all pairs before copying anything. Match the recording ID as well as time.
    for file in $files
        set -l name (path basename -- "$file")
        if not string match -rq '^(VID_[0-9]{8}_[0-9]{6}_[0-9]{2}_[0-9]+\.insv|LRV_[0-9]{8}_[0-9]{6}_01_[0-9]+\.lrv)$' -- "$name"
            printf 'Unrecognized camera filename: %s\n' "$file" >&2
            return 1
        end
        set -l directory (path dirname -- "$file")
        set -l key (string replace -r '^(VID|LRV)_([0-9]{8}_[0-9]{6})_[0-9]{2}_([0-9]+)\..*$' '$2_$3' -- "$name")
        if not contains -- "$directory/$key" $recordings
            set -a recordings "$directory/$key"
        end
        set -l video (string replace -r '^(.*)_([0-9]+)$' 'VID_$1_00_$2.insv' -- "$key")
        set -l proxy (string replace -r '^(.*)_([0-9]+)$' 'LRV_$1_01_$2.lrv' -- "$key")
        for partner in "$video" "$proxy"
            if not test -s "$directory/$partner"
                printf 'Missing or empty recording partner: %s\n' "$directory/$partner" >&2
                return 1
            end
        end
        set -l stamp (string replace -r '^(VID|LRV)_([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2})([0-9]{2}).*$' '$2-$3-$4T$5-$6' -- "$name")
        set -l target "$destination/$stamp/$name"
        if contains -- "$target" $targets
            printf 'Multiple source files map to: %s\n' "$target" >&2
            return 1
        end
        set -a targets "$target"
    end

    printf 'Ready: %d recordings, %d files -> %s\n' (count $recordings) (count $files) "$destination"
    set -l options --times --size-only --partial-dir=.rsync-partial --no-whole-file --mkpath --human-readable --itemize-changes --info=progress2 --outbuf=L
    if set -q _flag_dry_run
        set -a options --dry-run
    end
    for index in (seq (count $files))
        printf '\n[%d/%d] %s\n' $index (count $files) (path basename -- "$files[$index]")
        if set -q _flag_dry_run
            echo 'Previewing changes (filename and size)...'
        else
            echo 'Checking filename and size, then copying if needed...'
        end
        command rsync $options -- "$files[$index]" "$targets[$index]"
        set -l result $status
        if test $result -ne 0
            printf '\nFailed [%d/%d], rsync exit %d: %s\n' $index (count $files) $result "$files[$index]" >&2
            return $result
        end
        printf '\n[%d/%d] Finished.\n' $index (count $files)
    end
    if set -q _flag_dry_run
        echo 'Preview complete. No files copied.'
    else
        printf 'Complete: %d files checked/copied.\n' (count $files)
    end
end
