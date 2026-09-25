#!/usr/bin/env bash
# Refuse to push if any protected path is tracked by git.
#
# Reads the path list from tools/private-paths.txt. Exits non-zero, naming every
# offending file, when git is tracking something that must stay local. Run it by
# hand at any time, or let the pre-push hook run it (tools/install-hooks.sh).
#
# The list is default-deny. A plain line protects a path or a whole folder. A
# line starting with `!` carves one path back out, for the few files that are
# published on purpose out of an otherwise private folder. The blunt folder rule
# stays, so whatever private thing lands in that folder later is still covered.
#
# Run with --selftest to prove both directions against a throwaway repo.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
list="$repo_root/tools/private-paths.txt"

if [[ ! -f $list ]]; then
    echo "check-private-paths: missing $list" >&2
    exit 2
fi

# ------------------------------------------------------------------- selftest

# A guard with no fixture that proves it fires is not trustworthy. This builds a
# throwaway repo carrying the real path list, force-adds one carved-out path and
# one protected path, and asserts the guard passes on the first and blocks on the
# second.
selftest() {
    local script tmp rc fails=0
    script=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' RETURN

    git -C "$tmp" init -q
    mkdir -p "$tmp/tools" "$tmp/.claude/agents"
    cp "$list" "$tmp/tools/private-paths.txt"
    cp "$script" "$tmp/tools/check-private-paths.sh"

    # Direction one: a carved-out path is tracked, and the guard must allow it.
    echo "carved out on purpose" >"$tmp/.claude/agents/om-design-author.md"
    git -C "$tmp" add -f .claude/agents/om-design-author.md tools/private-paths.txt
    rc=0
    (cd "$tmp" && ./tools/check-private-paths.sh >/dev/null 2>&1) || rc=$?
    if ((rc != 0)); then
        echo "selftest FAIL: a carved-out path tripped the guard (exit $rc)" >&2
        fails=1
    else
        echo "selftest OK: a carved-out path does not trip the guard."
    fi

    # Direction two: a protected path is tracked, and the guard must block.
    echo "private" >"$tmp/.claude/settings.json"
    git -C "$tmp" add -f .claude/settings.json
    rc=0
    (cd "$tmp" && ./tools/check-private-paths.sh >/dev/null 2>&1) || rc=$?
    if ((rc != 1)); then
        echo "selftest FAIL: a protected path did not trip the guard (exit $rc)" >&2
        fails=1
    else
        echo "selftest OK: a protected path still trips the guard."
    fi

    return $fails
}

if [[ ${1:-} == --selftest ]]; then
    selftest
    exit $?
fi

# ---------------------------------------------------------------------- check

protected=()
carve_outs=()
while IFS= read -r line; do
    line=${line%%#*}
    line=$(echo "$line" | xargs || true)
    [[ -z $line ]] && continue
    if [[ ${line:0:1} == "!" ]]; then
        carve_outs+=("${line:1}")
    else
        protected+=("$line")
    fi
done <"$list"

# Tracked files the list explicitly publishes. Built first, so a protected
# folder rule can still name them without turning them into offenders.
declare -A published=()
for pattern in "${carve_outs[@]+"${carve_outs[@]}"}"; do
    while IFS= read -r tracked; do
        [[ -n $tracked ]] && published["$tracked"]=1
    done < <(git -C "$repo_root" ls-files -- "$pattern")
done

offenders=()
for pattern in "${protected[@]+"${protected[@]}"}"; do
    while IFS= read -r tracked; do
        [[ -z $tracked ]] && continue
        [[ -n ${published["$tracked"]:-} ]] && continue
        offenders+=("$tracked")
    done < <(git -C "$repo_root" ls-files -- "$pattern")
done

if ((${#offenders[@]})); then
    echo "BLOCKED: git is tracking paths that must never be pushed." >&2
    echo >&2
    printf '  %s\n' "${offenders[@]}" >&2
    echo >&2
    echo "These are listed in tools/private-paths.txt. To fix, untrack them and" >&2
    echo "keep the working copy:" >&2
    echo >&2
    echo "  git rm -r --cached <path>" >&2
    echo >&2
    echo "then make sure .gitignore covers the path and commit the removal." >&2
    exit 1
fi

echo "check-private-paths: OK, no protected path is tracked."
