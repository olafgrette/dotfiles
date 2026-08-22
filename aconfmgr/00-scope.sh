# Filesystem scope.
#
# Only /etc is managed. Pair each root with a descendant glob: aconfmgr's bare
# default ignores prune stray-file traversal but do not exclude modified files
# discovered later from package ownership. /efi is Lightshow's ESP;
# bin/lib/lib64/sbin are /usr compatibility symlinks.
for _aconf_root in \
    /bin /boot /dev /efi /home /lib /lib64 /media /mnt /opt /proc /root \
    /run /sbin /srv /sys /tmp /usr /var
do
    IgnorePath "$_aconf_root"
    IgnorePath "$_aconf_root/*"
done
unset _aconf_root

# Registry for exact managed /etc paths — wrappers record every CopyFile/
# CopyFileTo/CreateLink/SetFileProperty destination so 99-scope can derive
# its allowlist and ancestors without duplicating the path list.
_aconf_managed=()
if declare -f CopyFile >/dev/null 2>&1; then
    eval "$(declare -f CopyFile | sed 's/^CopyFile /_aconf_real_CopyFile /')"
fi
if declare -f CopyFileTo >/dev/null 2>&1; then
    eval "$(declare -f CopyFileTo | sed 's/^CopyFileTo /_aconf_real_CopyFileTo /')"
fi
if declare -f CreateLink >/dev/null 2>&1; then
    eval "$(declare -f CreateLink | sed 's/^CreateLink /_aconf_real_CreateLink /')"
fi
if declare -f SetFileProperty >/dev/null 2>&1; then
    eval "$(declare -f SetFileProperty | sed 's/^SetFileProperty /_aconf_real_SetFileProperty /')"
fi
CopyFile() { _aconf_managed+=("$1"); if declare -f _aconf_real_CopyFile >/dev/null 2>&1; then _aconf_real_CopyFile "$@"; fi; }
CopyFileTo() { _aconf_managed+=("$2"); if declare -f _aconf_real_CopyFileTo >/dev/null 2>&1; then _aconf_real_CopyFileTo "$@"; fi; }
CreateLink() { _aconf_managed+=("$1"); if declare -f _aconf_real_CreateLink >/dev/null 2>&1; then _aconf_real_CreateLink "$@"; fi; }
SetFileProperty() { _aconf_managed+=("$1"); if declare -f _aconf_real_SetFileProperty >/dev/null 2>&1; then _aconf_real_SetFileProperty "$@"; fi; }
