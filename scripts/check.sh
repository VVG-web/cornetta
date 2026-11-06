#!/bin/bash
# Full local gate. It never deploys, releases, pushes, or reads production data.
set -euo pipefail
cd "$(dirname "$0")/.."

export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_NOLOGO=1

section() {
  printf '\n==> %s\n' "$1"
}

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing $1. See docs/DEVELOPMENT.md." >&2
    exit 1
  }
}

for tool in shellcheck swiftlint swiftformat swift python3 dotnet; do
  require "$tool"
done

section "ShellCheck"
scripts=()
while IFS= read -r script; do scripts+=("$script"); done < <(find scripts windows/tools -type f -name '*.sh' -print | sort)
shellcheck --severity=error "${scripts[@]}"

section "SwiftLint"
mkdir -p test-results
if ! swiftlint lint --quiet >test-results/swiftlint.txt 2>&1; then
  cat test-results/swiftlint.txt
  exit 1
fi
printf 'SwiftLint findings, including legacy warnings: test-results/swiftlint.txt\n'

section "SwiftFormat"
swiftformat Sources Tests scripts/make-icon.swift --lint --quiet

section "Mac tests"
./scripts/test.sh

section "Mac universal package"
./scripts/build-dmg.sh
PACKAGE="dist/Cornetta-${VERSION:-0.0.0-dev}.dmg"
[ -f "$PACKAGE" ] || { echo "Missing package $PACKAGE" >&2; exit 1; }
codesign --verify "$PACKAGE"
MOUNT_ROOT="${JCODE_SCRATCH_DIR:-$HOME/.cache/jcode-cornetta}"
mkdir -p "$MOUNT_ROOT"
MOUNT=$(mktemp -d "$MOUNT_ROOT/cornetta-dmg.XXXXXX")
cleanup() { hdiutil detach "$MOUNT" >/dev/null 2>&1 || true; }
trap cleanup EXIT
hdiutil attach "$PACKAGE" -nobrowse -readonly -mountpoint "$MOUNT" >/dev/null
APP="$MOUNT/Cornetta.app"
[ -x "$APP/Contents/MacOS/Cornetta" ]
[ -d "$APP/Contents/Frameworks/Sparkle.framework" ]
[ "$(plutil -extract CFBundleIdentifier raw -o - "$APP/Contents/Info.plist")" = com.stellakamikaze.cornetta ]
[ "$(plutil -extract CFBundleVersion raw -o - "$APP/Contents/Info.plist")" = "${VERSION:-0.0.0-dev}" ]
[ -L "$MOUNT/Applicazioni" ]
[ "$(readlink "$MOUNT/Applicazioni")" = /Applications ]
lipo -info "$APP/Contents/MacOS/Cornetta" | grep -q arm64
lipo -info "$APP/Contents/MacOS/Cornetta" | grep -q x86_64
plutil -lint "$APP/Contents/Info.plist" >/dev/null
codesign --verify --deep --strict "$APP"
hdiutil detach "$MOUNT" >/dev/null
rmdir "$MOUNT"
trap - EXIT
printf 'Mounted package verified: %s (arm64 + x86_64, Sparkle, signature)\n' "$PACKAGE"

section "Windows tests (cross-platform)"
(cd windows && dotnet test Cornetta.Windows.sln)

section "Windows Release build"
(cd windows && dotnet build Cornetta.Windows.sln -c Release --no-restore)

section "Script tests"
python3 -m unittest discover -s scripts/tests

section "Worker tests"
NODE=$(source scripts/lib/guardia.sh && node22) || {
  echo "Node 22.13 or newer is required. Run nvm install && nvm use." >&2
  exit 1
}
(cd worker && "$NODE" --test)

if [ "${CORNETTA_SKIP_BROWSER:-0}" = 1 ]; then
  echo "Browser smoke tests skipped by CORNETTA_SKIP_BROWSER=1."
else
  section "Site browser smoke tests"
  PYTHON=python3
  [ ! -x .venv/bin/python ] || PYTHON=.venv/bin/python
  "$PYTHON" -c 'import playwright' 2>/dev/null || {
    echo "Playwright is missing. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt" >&2
    exit 1
  }
  "$PYTHON" scripts/test_site.py
fi

section "Repository hygiene"
git diff --check
printf 'All Cornetta checks passed.\n'
