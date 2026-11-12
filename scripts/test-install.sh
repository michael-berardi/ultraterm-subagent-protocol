#!/bin/sh
# Installer tests for scripts/install.sh (macOS and Linux). Run after scripts/build-release.sh.
# Every install goes into a temporary HOME under $USAP_TEST_TMP (default: $TMPDIR or /tmp), never the real home folder.
# The release is served from a local folder through file://, so no network is needed.
# Usage: scripts/test-install.sh [release-dir]      (default dist/release)
# Covered: fresh install and health check, re-install upgrades, corrupted archive refused, missing prerequisite named,
# git checkout with local changes protected, clean git checkout upgraded, unreachable release reported.
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

# 5. A git checkout with local changes is not overwritten.
H5="$WORK/h5"; mkdir "$H5"; T5="$(skills_of "$H5")/$NAME"
mkdir -p "$T5"; cp "$WORK/expect/SKILL.md" "$T5/SKILL.md"
( cd "$T5" && git init -q && git add SKILL.md && git -c user.name=usap-test -c user.email=usap-test@example.invalid commit -q -m "test checkout" )
printf 'local edit\n' >> "$T5/SKILL.md"
if run_install "$H5"; then fail "installer overwrote a git checkout with local changes"; fi
grep -q "local changes; it was not changed" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "dirty checkout did not get the protected-checkout message"; }
grep -q "local edit" "$T5/SKILL.md" || fail "dirty checkout's local edit was lost"
[ -d "$T5/.git" ] || fail "dirty checkout's .git was removed"
pass "git checkout with local changes is refused; its edit and history are kept"

# 6. A clean git checkout (the old `git clone` install) is upgraded.
git -C "$T5" checkout -q -- SKILL.md
run_install "$H5" || { cat "$WORK/last.log" >&2; fail "clean git checkout was not upgraded"; }
[ ! -e "$T5/.git" ] || fail "clean checkout was not replaced by the release copy"
cmp -s "$T5/SKILL.md" "$WORK/expect/SKILL.md" || fail "clean checkout was not replaced by the release SKILL.md"
pass "clean git checkout is upgraded to the release copy"

# 7. An unreachable release is reported by URL and installs nothing.
H7="$WORK/h7"; mkdir "$H7"
if run_install "$H7" "USAP_RELEASE_BASE=file://$WORK/no-such-release"; then fail "missing release was accepted"; fi
grep -q "download failed: file://$WORK/no-such-release/usap.tar.gz" "$WORK/last.log" || { cat "$WORK/last.log" >&2; fail "missing release was not named"; }
[ ! -e "$H7/.config" ] || fail "missing release still created a folder"
pass "unreachable release is named by URL; nothing installed"

echo "all installer tests passed for $VERSION"
