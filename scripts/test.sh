#!/bin/bash
# Lancia i test. Con i soli Command Line Tools il framework Testing va indicato a mano.
set -euo pipefail
cd "$(dirname "$0")/.."
DEV=/Library/Developer/CommandLineTools/Library/Developer
CLT=/Library/Developer/CommandLineTools
SELECTED=$(xcode-select -p)
# Con i Command Line Tools 27 il plugin delle macro di Testing sta in una sottocartella che swift non cerca.
# Con Xcode completo questi override mescolano framework e toolchain diversi: swift trova già tutto da solo.
PLUGIN=$CLT/usr/lib/swift/host/plugins/testing
EXTRA=()
if [ "$SELECTED" = "$CLT" ]; then
  [ -d "$PLUGIN" ] && EXTRA=(-Xswiftc -plugin-path -Xswiftc "$PLUGIN")
fi
if [ "$SELECTED" = "$CLT" ] && [ -d "$DEV/Frameworks/Testing.framework" ]; then
  swift test ${EXTRA[@]+"${EXTRA[@]}"} -Xswiftc -F -Xswiftc "$DEV/Frameworks" -Xlinker -F -Xlinker "$DEV/Frameworks" \
    -Xlinker -rpath -Xlinker "$DEV/Frameworks" -Xlinker -rpath -Xlinker "$DEV/usr/lib" "$@"
else
  swift test "$@"
fi
