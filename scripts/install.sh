#!/bin/sh
# USAP installer for macOS and Linux:
#   curl -fsSL https://github.com/michael-berardi/ultraterm-subagent-protocol/releases/latest/download/install.sh | sh
# Downloads the latest release (usap.tar.gz), checks its SHA-256 against SHA256SUMS, and installs the skill folder to
# ~/.config/agents/skills/ultraterm-subagent-protocol. USAP is text, so it needs no runtime, no Node and no Python.
# Re-running upgrades in place. A git checkout with local changes is never overwritten. Never uses sudo or edits shell profiles.
# Environment: USAP_SKILLS_DIR (default ~/.config/agents/skills), USAP_VERSION (pin, e.g. 1.4.1),
# USAP_RELEASE_BASE (override the download base URL, used by tests).
set -eu

REPO="michael-berardi/ultraterm-subagent-protocol"
NAME="ultraterm-subagent-protocol"

say() { printf '%s\n' "$*"; }
die() { printf 'usap install: %s\n' "$*" >&2; exit 1; }

# The version the skill declares: `  version: 1.4.1` in its SKILL.md metadata.
skill_version() { sed -n 's/^  version:[[:space:]]*\([0-9][0-9A-Za-z.+-]*\)[[:space:]]*$/\1/p' "$1" | head -n 1; }

main() {
[ -n "${HOME:-}" ] || die "HOME is not set; set HOME to your home folder and run this again"

SKILLS_DIR="${USAP_SKILLS_DIR:-$HOME/.config/agents/skills}"
case "$SKILLS_DIR" in /*) ;; *) SKILLS_DIR="$(pwd)/$SKILLS_DIR" ;; esac
if [ -n "${USAP_RELEASE_BASE:-}" ]; then BASE="$USAP_RELEASE_BASE"
elif [ -n "${USAP_VERSION:-}" ]; then BASE="https://github.com/$REPO/releases/download/v${USAP_VERSION#v}"
else BASE="https://github.com/$REPO/releases/latest/download"; fi

# Prerequisites first, so a missing tool is named before anything is downloaded.
if command -v curl >/dev/null 2>&1; then fetch() { curl -fsSL --retry 3 -o "$2" "$1" || die "download failed: $1"; }
elif command -v wget >/dev/null 2>&1; then fetch() { wget -q -O "$2" "$1" || die "download failed: $1"; }
else die "needs curl or wget, and neither is installed. On macOS curl comes with the system; on Debian or Ubuntu run: sudo apt-get install curl"; fi
command -v tar >/dev/null 2>&1 || die "needs tar, which is not installed. Install it with your package manager (on Debian or Ubuntu: sudo apt-get install tar), then run this again"
if command -v sha256sum >/dev/null 2>&1; then sha256() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }
else die "needs sha256sum or shasum to check the download. On Debian or Ubuntu run: sudo apt-get install coreutils"; fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/usap-install.XXXXXX") || die "cannot create a temporary folder in ${TMPDIR:-/tmp}"
STAGE=""
cleanup() { rm -rf "$TMP"; if [ -n "$STAGE" ]; then rm -rf "$STAGE"; fi; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# expect <file> <name> <sums-file>: the file's SHA-256 must equal the line for <name> in the sums file.
expect() {
  want=$(awk -v n="$2" '{ f=$2; sub(/^\*/, "", f); if (f == n) print $1 }' "$3")
  [ -n "$want" ] || die "no checksum for $2 in SHA256SUMS; the release is incomplete. Nothing was installed"
  got=$(sha256 "$1")
  [ "$got" = "$want" ] || die "checksum mismatch for $2 (expected $want, got $got); nothing was installed"
}

say "Downloading USAP..."
fetch "$BASE/usap.tar.gz" "$TMP/usap.tar.gz"
fetch "$BASE/SHA256SUMS" "$TMP/SHA256SUMS"
expect "$TMP/usap.tar.gz" usap.tar.gz "$TMP/SHA256SUMS"

mkdir "$TMP/src"
tar -xzf "$TMP/usap.tar.gz" -C "$TMP/src" || die "cannot unpack the download; nothing was installed"
[ -f "$TMP/src/SKILL.md" ] || die "the download is not a USAP release (no SKILL.md inside); nothing was installed"
got_name=$(sed -n 's/^name:[[:space:]]*//p' "$TMP/src/SKILL.md" | head -n 1)
[ "$got_name" = "$NAME" ] || die "the download is for '$got_name', not $NAME; nothing was installed"
VERSION=$(skill_version "$TMP/src/SKILL.md")
[ -n "$VERSION" ] || die "cannot read the version from SKILL.md in the download; nothing was installed"

TARGET="$SKILLS_DIR/$NAME"
# A git checkout (for example one made with `git clone`) is upgraded only when it has no local changes.
if [ -e "$TARGET/.git" ]; then
  command -v git >/dev/null 2>&1 || die "$TARGET is a git checkout, and git is not installed to check its local changes; nothing was changed"
  changes=$(git -C "$TARGET" status --porcelain 2>&1) || die "cannot read the git status of $TARGET ($changes); nothing was changed"
  [ -z "$changes" ] || die "$TARGET is a git checkout with local changes; it was not changed. Commit, stash or move those changes aside, then run this again"
fi
PREVIOUS=""
if [ -f "$TARGET/SKILL.md" ]; then PREVIOUS=$(skill_version "$TARGET/SKILL.md"); fi

mkdir -p "$SKILLS_DIR" || die "cannot create $SKILLS_DIR; set USAP_SKILLS_DIR to a folder you can write to"
STAGE="$SKILLS_DIR/.$NAME.new.$$"
rm -rf "$STAGE"
mv "$TMP/src" "$STAGE" || die "cannot stage the download in $SKILLS_DIR; nothing was changed"

# Swap the folders with renames: the old copy moves aside, the new one moves in, then the old one goes.
if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  BACKUP="$SKILLS_DIR/.$NAME.old.$$"
  mv "$TARGET" "$BACKUP" || die "cannot move the previous copy aside at $TARGET; nothing was changed"
  if ! mv "$STAGE" "$TARGET"; then
    mv "$BACKUP" "$TARGET" || die "cannot put the new copy in place at $TARGET, and the previous copy is at $BACKUP"
    die "cannot put the new copy in place at $TARGET; the previous copy was restored"
  fi
  STAGE=""
  rm -rf "$BACKUP"
else
  mv "$STAGE" "$TARGET" || die "cannot put the new copy in place at $TARGET; nothing was changed"
  STAGE=""
fi

# Health check: the installed SKILL.md must declare the version that was downloaded.
INSTALLED=$(skill_version "$TARGET/SKILL.md")
[ "$INSTALLED" = "$VERSION" ] || die "the installed copy at $TARGET reports '${INSTALLED:-no version}', not $VERSION"

if [ -n "$PREVIOUS" ]; then say "Upgraded USAP from $PREVIOUS to $VERSION."
else say "USAP $VERSION installed."; fi
say "Installed at: $TARGET"
say "Check: $TARGET/SKILL.md declares USAP $INSTALLED (ok)"
say "Next: in your agent, say: Use the UltraTerm Subagent Protocol for this task."
}

main "$@"
