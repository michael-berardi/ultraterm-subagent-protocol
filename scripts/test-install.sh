#!/bin/sh
# Installer tests for scripts/install.sh (macOS and Linux). Run after scripts/build-release.sh.
# Every install goes into a temporary HOME under $USAP_TEST_TMP (default: $TMPDIR or /tmp), never the real home folder.
# The release is served from a local folder through file://, so no network is needed.
# Usage: scripts/test-install.sh [release-dir]      (default dist/release)
# Covered: fresh install and health check, re-install upgrades, corrupted archive refused, missing prerequisite named,
# git checkouts never swapped (local changes, unpushed commit, stash, diverged, no upstream; clean ones fast-forwarded), symlink refused, unreachable release reported.
set -eu
cd "$(dirname "$0")/.."

pass() { printf 'ok - %s\n' "$1"; }
fail() { printf 'FAIL - %s\n' "$1" >&2; exit 1; }

DIST_ARG="${1:-dist/release}"
DIST=$(cd "$DIST_ARG" 2>/dev/null && pwd) || fail "no release folder at $DIST_ARG; run scripts/build-release.sh first"
for f in usap.tar.gz usap.zip install.sh install.ps1 SHA256SUMS; do
  [ -f "$DIST/$f" ] || fail "release folder is missing $f"
done
WORK=$(mktemp -d "${USAP_TEST_TMP:-${TMPDIR:-/tmp}}/usap-test.XXXXXX") || fail "cannot create a test folder"
trap 'rm -rf "$WORK"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

NAME=ultraterm-subagent-protocol
BASE="file://$DIST"
INSTALLER="$DIST/install.sh"

# The version the release itself declares, read from its archive.
mkdir "$WORK/expect"
tar -xzf "$DIST/usap.tar.gz" -C "$WORK/expect" || fail "release archive does not unpack"
VERSION=$(sed -n 's/^  version:[[:space:]]*\([0-9][0-9A-Za-z.+-]*\)[[:space:]]*$/\1/p' "$WORK/expect/SKILL.md" | head -n 1)
[ -n "$VERSION" ] || fail "release SKILL.md declares no version"
if tar -tzf "$DIST/usap.tar.gz" | grep -Eq '^(\./)?(tests|scripts)/'; then fail "release archive contains tests or scripts"; fi
pass "release archive unpacks, declares version $VERSION, and omits tests and scripts"

# run_install <home> [VAR=value ...]: runs the shipped installer with a clean environment; output goes to $WORK/last.log.
run_install() {
  h="$1"; shift
  env -i PATH="$PATH" TMPDIR="$WORK" HOME="$h" USAP_SKILLS_DIR="$h/.config/agents/skills" \
    USAP_RELEASE_BASE="$BASE" "$@" sh "$INSTALLER" >"$WORK/last.log" 2>&1
}
skills_of() { echo "$1/.config/agents/skills"; }
# No leftover staging or backup folders next to the installed copy.
no_leftovers() { [ -z "$(find "$1" -mindepth 1 -maxdepth 1 -name '.*' 2>/dev/null)" ]; }

# 1. Fresh install into an empty home.
H1="$WORK/h1"; mkdir -p "$H1"
run_install "$H1" || { cat "$WORK/last.log" >&2; fail "fresh install exited non-zero"; }
grep -q "USAP $VERSION installed\." "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "fresh install did not report $VERSION"; }
T1="$(skills_of "$H1")/$NAME"
cmp -s "$T1/SKILL.md" "$WORK/expect/SKILL.md" || fail "installed SKILL.md differs from the release"
[ ! -e "$T1/tests" ] && [ ! -e "$T1/scripts" ] || fail "installed copy contains tests or scripts"
[ "$(ls -A "$(skills_of "$H1")")" = "$NAME" ] || fail "fresh install left extra entries in the skills folder"
no_leftovers "$(skills_of "$H1")" || fail "fresh install left a staging folder"
grep -q "Check: .*SKILL.md declares USAP $VERSION (ok)" "$WORK/last.log" || fail "health check line missing from the output"
pass "fresh install: $VERSION installed at $T1, health check passes, nothing left behind"

# 2. Re-running upgrades in place. Pretend the installed copy is an older release first.
sed 's/^  version: .*/  version: 0.0.1/' "$WORK/expect/SKILL.md" > "$WORK/old-SKILL.md"
cat "$WORK/old-SKILL.md" > "$T1/SKILL.md"
run_install "$H1" || { cat "$WORK/last.log" >&2; fail "re-install exited non-zero"; }
grep -q "Upgraded USAP from 0.0.1 to $VERSION\." "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "re-install did not report the upgrade"; }
cmp -s "$T1/SKILL.md" "$WORK/expect/SKILL.md" || fail "re-install did not restore the release SKILL.md"
[ "$(ls -A "$(skills_of "$H1")")" = "$NAME" ] || fail "re-install left extra entries in the skills folder"
pass "re-install upgrades 0.0.1 to $VERSION in place"

# 3. A corrupted archive is refused before anything is installed; the existing copy is untouched.
BAD="$WORK/bad"; mkdir "$BAD"
cp "$DIST/usap.tar.gz" "$DIST/usap.zip" "$DIST/install.sh" "$DIST/install.ps1" "$DIST/SHA256SUMS" "$BAD/"
printf 'corrupted' >> "$BAD/usap.tar.gz"
before=$(cksum < "$T1/SKILL.md")
if run_install "$H1" "USAP_RELEASE_BASE=file://$BAD"; then fail "corrupted archive was accepted"; fi
grep -q "checksum mismatch for usap.tar.gz" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "corrupted archive did not fail with the checksum error"; }
[ "$before" = "$(cksum < "$T1/SKILL.md")" ] || fail "corrupted archive changed the installed copy"
no_leftovers "$(skills_of "$H1")" || fail "corrupted archive left a staging folder"
pass "corrupted archive refused with the checksum error; installed copy unchanged"

# 4. A missing prerequisite is named, and nothing is downloaded or installed.
EMPTY="$WORK/emptybin"; mkdir "$EMPTY"; H4="$WORK/h4"; mkdir "$H4"
if env -i PATH="$EMPTY" TMPDIR="$WORK" HOME="$H4" /bin/sh "$INSTALLER" >"$WORK/last.log" 2>&1; then
  fail "installer ran with no curl or wget"
fi
grep -q "needs curl or wget" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "missing curl/wget was not named"; }
[ ! -e "$H4/.config" ] || fail "missing prerequisite still created a folder"
pass "missing curl or wget is named; nothing installed"

# 5. Git checkouts. Each is a clone of a local "origin" so that git pull --ff-only has somewhere to pull from.
GITC="git -c user.name=usap-test -c user.email=usap-test@example.invalid"
ORIGIN="$WORK/origin.git"
git init -q --bare "$ORIGIN"
SEED="$WORK/seed"; git init -q "$SEED"
cp "$WORK/expect/SKILL.md" "$SEED/SKILL.md"
( cd "$SEED" && git add SKILL.md && $GITC commit -q -m "seed" && git push -q "$ORIGIN" HEAD:refs/heads/main )
git -C "$ORIGIN" symbolic-ref HEAD refs/heads/main
clone_into() { rm -rf "$1"; mkdir -p "$(dirname "$1")"; git clone -q "$ORIGIN" "$1"; }

# 5a. Local changes: refused, edit and .git kept.
H5="$WORK/h5"; mkdir "$H5"; T5="$(skills_of "$H5")/$NAME"
clone_into "$T5"
printf 'local edit\n' >> "$T5/SKILL.md"
if run_install "$H5"; then fail "installer overwrote a git checkout with local changes"; fi
grep -q "local changes; it was not changed" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "dirty checkout did not get the protected-checkout message"; }
grep -q "local edit" "$T5/SKILL.md" || fail "dirty checkout's local edit was lost"
[ -d "$T5/.git" ] || fail "dirty checkout's .git was removed"
pass "git checkout with local changes is refused; its edit and history are kept"
git -C "$T5" checkout -q -- SKILL.md

# 5b. A clean checkout with an unpushed local commit is kept as a git checkout and keeps that commit.
printf 'extra\n' > "$T5/notes.txt"
( cd "$T5" && git add notes.txt && $GITC commit -q -m "unpushed local work" )
mine=$(git -C "$T5" rev-parse HEAD)
run_install "$H5" || { cat "$WORK/last.log" >&2; fail "clean checkout with a local commit was refused"; }
[ -d "$T5/.git" ] || fail "install removed the .git folder of a clean checkout"
[ "$(git -C "$T5" rev-parse HEAD)" = "$mine" ] || fail "install moved HEAD of a checkout with a local commit"
git -C "$T5" cat-file -e "$mine" 2>/dev/null && [ -f "$T5/notes.txt" ] || fail "unpushed local commit was lost"
no_leftovers "$(skills_of "$H5")" || fail "checkout update left a staging folder"
pass "clean git checkout with an unpushed commit keeps its commit and .git"

# 5c. A clone with a stash is not replaced and keeps the stash.
printf 'wip\n' >> "$T5/SKILL.md"
git -C "$T5" stash push -q -m wip
[ -n "$(git -C "$T5" stash list)" ] || fail "test setup: no stash was made"
run_install "$H5" || { cat "$WORK/last.log" >&2; fail "clean checkout with a stash was refused"; }
[ -d "$T5/.git" ] && [ -n "$(git -C "$T5" stash list)" ] || fail "install lost the stash of a checkout"
pass "git checkout with a stash is not replaced; the stash is kept"
git -C "$T5" stash drop -q

# 5d. A clean checkout behind origin is fast-forwarded in place, history intact.
H6="$WORK/h6"; mkdir "$H6"; T6="$(skills_of "$H6")/$NAME"
clone_into "$T6"
( cd "$SEED" && printf 'more\n' > more.txt && git add more.txt && $GITC commit -q -m "upstream" && git push -q "$ORIGIN" HEAD:refs/heads/main )
run_install "$H6" || { cat "$WORK/last.log" >&2; fail "clean checkout behind origin was not updated"; }
[ -d "$T6/.git" ] && [ -f "$T6/more.txt" ] || fail "checkout was not fast-forwarded in place"
pass "clean git checkout behind origin is fast-forwarded in place"

# 5e. A checkout that cannot fast-forward (diverged) is refused and unchanged.
H8="$WORK/h8"; mkdir "$H8"; T8="$(skills_of "$H8")/$NAME"
clone_into "$T8"
( cd "$T8" && printf 'mine\n' > mine.txt && git add mine.txt && $GITC commit -q -m "local" )
( cd "$SEED" && printf 'x\n' > x.txt && git add x.txt && $GITC commit -q -m "upstream 2" && git push -q "$ORIGIN" HEAD:refs/heads/main )
mine=$(git -C "$T8" rev-parse HEAD)
if run_install "$H8"; then fail "diverged checkout was accepted"; fi
grep -q "git pull --ff-only failed" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "diverged checkout did not get the pull message"; }
[ "$(git -C "$T8" rev-parse HEAD)" = "$mine" ] && [ -d "$T8/.git" ] || fail "diverged checkout was changed"
pass "checkout that cannot fast-forward is refused and unchanged"

# 5f. A checkout without an upstream (git init) is refused, not replaced.
H9="$WORK/h9"; mkdir "$H9"; T9="$(skills_of "$H9")/$NAME"
mkdir -p "$T9"; cp "$WORK/expect/SKILL.md" "$T9/SKILL.md"
( cd "$T9" && git init -q && git add SKILL.md && $GITC commit -q -m "local only" )
if run_install "$H9"; then fail "checkout without upstream was accepted"; fi
[ -d "$T9/.git" ] || fail "checkout without upstream lost .git"
pass "checkout without an upstream is refused and kept"

# 6. A symlinked skill folder is refused and its target is untouched.
H10="$WORK/h10"; mkdir -p "$(skills_of "$H10")" "$WORK/real-skill"
printf 'precious\n' > "$WORK/real-skill/keep.txt"
ln -s "$WORK/real-skill" "$(skills_of "$H10")/$NAME"
if run_install "$H10"; then fail "symlinked skill folder was accepted"; fi
grep -q "symbolic link to $WORK/real-skill" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "symlink refusal did not print the link target"; }
[ -L "$(skills_of "$H10")/$NAME" ] && [ -f "$WORK/real-skill/keep.txt" ] || fail "symlink or its target was changed"
pass "symlinked skill folder is refused; link and target untouched"

# 7. An unreachable release is reported by URL and installs nothing.
H7="$WORK/h7"; mkdir "$H7"
if run_install "$H7" "USAP_RELEASE_BASE=file://$WORK/no-such-release"; then fail "missing release was accepted"; fi
grep -q "download failed: file://$WORK/no-such-release/usap.tar.gz" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "missing release was not named"; }
[ ! -e "$H7/.config" ] || fail "missing release still created a folder"
pass "unreachable release is named by URL; nothing installed"

echo "all installer tests passed for $VERSION"
