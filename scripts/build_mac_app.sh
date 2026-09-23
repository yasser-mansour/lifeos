#!/usr/bin/env bash
# Builds desktop/LIFEOS.app from the Swift sources in desktop/LIFEOSLauncher.
# No Xcode project required — compiled directly with swiftc.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/desktop"
APP_BUNDLE="$DESKTOP_DIR/LIFEOS.app"

if ! command -v swiftc >/dev/null 2>&1; then
  echo "swiftc not found. Install Xcode Command Line Tools: xcode-select --install" >&2
  exit 1
fi

echo "==> Generating app icon"
if [ -f "$ROOT_DIR/.venv/bin/python" ] && "$ROOT_DIR/.venv/bin/python" -c "import PIL" >/dev/null 2>&1; then
  "$ROOT_DIR/.venv/bin/python" "$DESKTOP_DIR/generate_icon.py"
  iconutil -c icns "$DESKTOP_DIR/AppIcon.iconset" -o "$DESKTOP_DIR/AppIcon.icns"
else
  echo "    Pillow not available in .venv — skipping icon generation (app will use the default icon)."
fi

echo "==> Generating build config (bakes in the repo path — LIFEOS.app is movable, see BackendManager.swift)"
mkdir -p "$DESKTOP_DIR/build"
cat > "$DESKTOP_DIR/build/BuildConfig.swift" <<EOF
enum BuildConfig {
    static let repoRootPath = "$ROOT_DIR"
}
EOF

echo "==> Compiling Swift sources"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"

swiftc -O \
  -o "$APP_BUNDLE/Contents/MacOS/LIFEOSLauncher" \
  "$DESKTOP_DIR"/LIFEOSLauncher/*.swift \
  "$DESKTOP_DIR/build/BuildConfig.swift" \
  -framework Cocoa -framework WebKit

cp "$DESKTOP_DIR/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
if [ -f "$DESKTOP_DIR/AppIcon.icns" ]; then
  cp "$DESKTOP_DIR/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
fi

# ad-hoc signature so Gatekeeper doesn't flag a completely unsigned binary
# on the same Mac it was built on (no Developer ID needed for local use).
if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$APP_BUNDLE" >/dev/null 2>&1 || true
fi

echo ""
echo "Built: $APP_BUNDLE"
echo "Launch it with: open \"$APP_BUNDLE\""
