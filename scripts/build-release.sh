#!/bin/sh
# Builds the download assets for the current commit into <out> (default dist/release):
#   usap.tar.gz   the skill folder (git archive of HEAD without tests/ and scripts/), installed by install.sh
#   usap.zip      the same folder as a zip, installed by install.ps1 (Expand-Archive needs no tar)
#   install.sh, install.ps1   the installers
#   SHA256SUMS    checksums of the four files above
# Usage: scripts/build-release.sh [out-dir]   (run from a clean checkout of the release tag)
set -eu
cd "$(dirname "$0")/.."
OUT="${1:-dist/release}"
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "build-release: the working tree has changes; build from a clean checkout" >&2; exit 1; }
rm -rf "$OUT"; mkdir -p "$OUT"
# Deterministic: git archive takes the commit time and fixed owners; gzip -n drops its name and time.
git archive --format=tar HEAD -- . ':(exclude)tests' ':(exclude)scripts' | gzip -n > "$OUT/usap.tar.gz"
git archive --format=zip HEAD -- . ':(exclude)tests' ':(exclude)scripts' > "$OUT/usap.zip"
cp scripts/install.sh scripts/install.ps1 "$OUT/"
if command -v sha256sum >/dev/null 2>&1; then
  ( cd "$OUT" && sha256sum usap.tar.gz usap.zip install.sh install.ps1 > SHA256SUMS )
else
  ( cd "$OUT" && shasum -a 256 usap.tar.gz usap.zip install.sh install.ps1 > SHA256SUMS )
fi
echo "built $OUT for $(git rev-parse --short HEAD)"; ls -l "$OUT"
