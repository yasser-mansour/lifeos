#!/usr/bin/env bash
# Builds the LIFEOS Android debug APK.
# Output: android/app/build/outputs/apk/debug/app-debug.apk
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANDROID_DIR="$ROOT_DIR/android"

if [ -z "${ANDROID_HOME:-}" ]; then
  if [ -d "/opt/homebrew/share/android-commandlinetools" ]; then
    export ANDROID_HOME="/opt/homebrew/share/android-commandlinetools"
  else
    echo "ANDROID_HOME is not set and no SDK was found at the default Homebrew path." >&2
    echo "Install it with: brew install --cask android-commandlinetools" >&2
    exit 1
  fi
fi

cd "$ANDROID_DIR"

if [ ! -f "./gradlew" ]; then
  echo "gradlew not found in $ANDROID_DIR — run 'gradle wrapper' once first." >&2
  exit 1
fi

echo "Building LIFEOS Android debug APK…"
./gradlew assembleDebug --console=plain

APK_PATH="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK_PATH" ]; then
  echo ""
  echo "Built: $APK_PATH"
  echo "Install on a connected device/emulator with:"
  echo "  adb install -r \"$APK_PATH\""
else
  echo "Build reported success but the APK was not found at the expected path." >&2
  exit 1
fi
