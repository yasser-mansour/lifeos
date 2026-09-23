# LIFEOS for Android

Native Kotlin + Jetpack Compose, offline-first via Room, syncing with the Mac backend over the LAN. See [`../docs/SYNC.md`](../docs/SYNC.md) and [`../docs/DEVICES.md`](../docs/DEVICES.md) for how syncing and pairing actually work.

## Build

```bash
../scripts/build_android.sh
```

or directly:

```bash
./gradlew assembleDebug
```

Output: `app/build/outputs/apk/debug/app-debug.apk`.

Requires the Android SDK (`ANDROID_HOME`) with `platforms;android-35` and `build-tools;35.0.0` — `build_android.sh` looks for it at the standard Homebrew path (`brew install --cask android-commandlinetools`) if `ANDROID_HOME` isn't already set.

## Install

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Or open this directory in Android Studio and run it directly on a device or emulator.

## Architecture

```
Compose UI (ui/*)
    ↓
ViewModel (one per screen, manual DI via LifeOSViewModelFactory)
    ↓
Repository (data/repository/*) — reads/writes Room first, always
    ↓
Room (data/local/*)  ←──sync──→  Retrofit (data/remote/*) → Django backend
```

Every repository method is local-first: it writes to Room and returns immediately, never blocking on network. `sync/SyncWorker.kt` (WorkManager, periodic + on-demand) is the only thing that talks to the network on its own initiative — see [`../docs/SYNC.md`](../docs/SYNC.md).

The Study timer (`study/StudyTimerEngine.kt`, `study/StudyTimerService.kt`) is a from-scratch Kotlin port of the backend's event-replay duration algorithm (`backend/apps/study/engine.py`) — see [`../docs/STUDY_ENGINE.md`](../docs/STUDY_ENGINE.md) for why duration is computed from events rather than a live counter, which is what lets an active session survive the app being backgrounded, the screen locking, or the process being killed and restarted.

## Tests

```bash
./gradlew testDebugUnitTest
```

`StudyTimerEngineTest.kt` (10 tests) mirrors the backend's own timer-engine test cases — same scenarios, same expected durations, on both platforms independently.

Instrumented tests (`src/androidTest`) and a full device/emulator run were not exercised in the build environment this project was built in — no emulator was available to boot there. See the root README's Known Limitations and the project's build report for exactly what was and wasn't verified.

## Permissions

`CAMERA` (QR pairing scan only — requested when you open Devices → Pair, not at app launch), `POST_NOTIFICATIONS` (the active-session notification), `FOREGROUND_SERVICE` (keeping the study timer's notification current while backgrounded), `INTERNET`/network-state (talking to the Mac). No permission is requested until the feature that needs it is actually used.
