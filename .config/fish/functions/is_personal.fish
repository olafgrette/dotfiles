function is_personal --description 'test the repository personal-host allowlist'
    set -l source (path resolve (status filename)); or return 1
    set -l root (path dirname (path dirname (path dirname (path dirname $source))))
    set -l host (command uname -n); or return 1
    set host (string split . -- $host)[1]
    test -n "$host"; and test -f "$root/personal-hosts"; or return 1
    command grep -qxF -- "$host" "$root/personal-hosts"
end
