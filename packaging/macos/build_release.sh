#!/usr/bin/env bash
# Builds the DISTRIBUTABLE LIFEOS.app + .dmg — a fully self-contained bundle
# with Python/Django/every dependency embedded, needing no system Python, no
# venv, no sibling repo checkout on the machine that runs it.
#
# This is separate from scripts/build_mac_app.sh (the thin dev-mode launcher
# that shells out to this repo's own .venv) — that script, and the normal
# day-to-day dev workflow it supports, are untouched by this one.
#
# Usage: packaging/macos/build_release.sh [version]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/desktop"
VERSION="${1:-0.1.0}"
RELEASE_DIR="$ROOT_DIR/packaging/macos/dist"
APP_BUNDLE="$RELEASE_DIR/LIFEOS.app"

if ! command -v swiftc >/dev/null 2>&1; then
  echo "swiftc not found. Install Xcode Command Line Tools: xcode-select --install" >&2
  exit 1
fi
if [ ! -x "$ROOT_DIR/.venv/bin/pyinstaller" ]; then
  echo "pyinstaller not found in .venv. Install it: .venv/bin/pip install pyinstaller" >&2
  exit 1
fi

rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

echo "==> [1/6] Bundling the backend with PyInstaller (Python + Django + every dependency)"
"$ROOT_DIR/.venv/bin/pyinstaller" "$ROOT_DIR/packaging/macos/lifeos-backend.spec" \
  --noconfirm \
  --distpath "$RELEASE_DIR/_pyinstaller_dist" \
  --workpath "$RELEASE_DIR/_pyinstaller_build"

echo "==> [2/6] Generating app icon"
if [ -f "$ROOT_DIR/.venv/bin/python" ] && "$ROOT_DIR/.venv/bin/python" -c "import PIL" >/dev/null 2>&1; then
  "$ROOT_DIR/.venv/bin/python" "$DESKTOP_DIR/generate_icon.py"
  iconutil -c icns "$DESKTOP_DIR/AppIcon.iconset" -o "$DESKTOP_DIR/AppIcon.icns"
else
  echo "    Pillow not available in .venv — skipping icon generation (app will use the default icon)."
fi

echo "==> [3/6] Compiling the Swift launcher (release build config — no dev repo path baked in)"
mkdir -p "$RELEASE_DIR/_build"
cat > "$RELEASE_DIR/_build/BuildConfig.swift" <<EOF
enum BuildConfig {
    // Unused in a distributable build — BackendManager finds the bundled
    // backend at Contents/Resources/lifeos-backend/ instead and never
    // reads this. Kept only because the dev fallback code path references
    // the symbol; see BackendManager.swift.
    static let repoRootPath = ""
}
EOF

mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
swiftc -O \
  -o "$APP_BUNDLE/Contents/MacOS/LIFEOSLauncher" \
  "$DESKTOP_DIR"/LIFEOSLauncher/*.swift \
  "$RELEASE_DIR/_build/BuildConfig.swift" \
  -framework Cocoa -framework WebKit

echo "==> [4/6] Assembling the app bundle"
cp "$DESKTOP_DIR/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
# Distributable builds carry their own version, independent of the dev
# checkout's Info.plist (which isn't versioned per-release).
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || true
if [ -f "$DESKTOP_DIR/AppIcon.icns" ]; then
  cp "$DESKTOP_DIR/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
fi
cp -R "$RELEASE_DIR/_pyinstaller_dist/lifeos-backend" "$APP_BUNDLE/Contents/Resources/lifeos-backend"
rm -rf "$RELEASE_DIR/_pyinstaller_dist" "$RELEASE_DIR/_pyinstaller_build" "$RELEASE_DIR/_build"

echo "==> [5/6] Signing (ad-hoc — no Apple Developer ID configured on this machine, see docs)"
SIGN_IDENTITY="-"
if security find-identity -v -p codesigning 2>/dev/null | grep -q "Developer ID Application"; then
  SIGN_IDENTITY=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | sed -E 's/.*"(.*)"/\1/')
  echo "    Found Developer ID identity — signing for real: $SIGN_IDENTITY"
else
  echo "    No Developer ID identity found — ad-hoc signing only. Gatekeeper will warn on first launch (see README)."
fi
codesign --force --deep --sign "$SIGN_IDENTITY" "$APP_BUNDLE"

echo "==> [6/6] Building .dmg"
DMG_NAME="LIFEOS-$VERSION.dmg"
DMG_STAGING="$RELEASE_DIR/_dmg_staging"
mkdir -p "$DMG_STAGING"
cp -R "$APP_BUNDLE" "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"
hdiutil create -volname "LIFEOS $VERSION" -srcfolder "$DMG_STAGING" -ov -format UDZO "$RELEASE_DIR/$DMG_NAME"
rm -rf "$DMG_STAGING"

shasum -a 256 "$RELEASE_DIR/$DMG_NAME" > "$RELEASE_DIR/SHA256SUMS.txt"

echo ""
echo "Built: $RELEASE_DIR/$DMG_NAME"
echo "App bundle (unpacked, for inspection/testing): $APP_BUNDLE"
cat "$RELEASE_DIR/SHA256SUMS.txt"
