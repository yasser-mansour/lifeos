# LIFEOS

A private operating system for your life. Manage your tasks, focus, projects, money, people, notes, and more — locally on your computer.

## Download LIFEOS

### macOS
Download the latest `.dmg` from the [Releases page](../../releases/latest), open it, and drag LIFEOS into Applications.

### Windows
Download the latest `LIFEOS-Setup-*.exe` from the [Releases page](../../releases/latest) and run it.

You don't need to download the source code, install Python, or use a terminal. See [Installing](#installing) below for the exact steps, including what the first-launch security warning looks like on an unsigned beta build.

## Why LIFEOS

School, study, tasks, projects, finance (personal and business), journal, writing, and everything else that would otherwise live scattered across a dozen apps and your own memory — in one place, on your own computer.

- **Your data stays on your computer.** There's no LIFEOS account, no cloud database, no server this talks to.
- **Every installation is independent.** Your LIFEOS and a friend's LIFEOS never see each other's data, ever.
- **It's a real desktop app.** No terminal, no browser tab you have to remember to open — a normal window, a normal icon, quits like anything else.

## Installing

### macOS
1. Download the `.dmg` from [Releases](../../releases/latest).
2. Open it and drag **LIFEOS** into **Applications**.
3. Open LIFEOS from Applications (or Spotlight).
4. Because this beta build isn't signed with an Apple Developer ID yet, macOS will say the app is "from an unidentified developer" the first time. Right-click (or Control-click) the app → **Open** → **Open** again in the dialog. You only need to do this once. This is expected for now — see [Limitations](#limitations) — and the README will never tell you to disable Gatekeeper globally.
5. Complete the short setup (your name, a passcode, what you want LIFEOS to manage).

### Windows
1. Download `LIFEOS-Setup-*.exe` from [Releases](../../releases/latest).
2. Run it. Because this beta build isn't code-signed yet, Windows SmartScreen may show "Windows protected your PC." Click **More info** → **Run anyway**. This is expected for now — the README will never tell you to disable Windows Defender.
3. Follow the installer (no administrator password needed — it installs just for your account).
4. Open LIFEOS from the Start Menu.
5. Complete the short setup.

Either way, LIFEOS creates its own empty, private database on first launch — nothing is pre-filled, nothing is shared with anyone else who installs it.

## What you can manage

Tasks, Focus (a timer for deep work), Projects, Finance (personal and business, accounts and funds kept separate from what they're *for*), People & Organizations, Notes, School, Journal, Writing, Calendar, and Goals. Pick what you want during setup — turning something off later just hides it from the sidebar, it never deletes anything.

## Backups

Settings → Backup & Restore lets you create a backup, see your existing ones, and restore any of them (which safety-backs-up your current state first, automatically). LIFEOS also backs up automatically before applying an update that changes your data's structure — you're never asked to do this yourself for an ordinary update.

## FAQ

**Do I need to install anything else?** No — not Python, not a database, nothing. The download is the whole app.

**Where's my data?** Entirely on your own computer (macOS: `~/Library/Application Support/LIFEOS`; Windows: `%LOCALAPPDATA%\LIFEOS`). Uninstalling LIFEOS does not delete it.

**Does this need the internet?** No, other than to download the app itself. Everything runs locally.

**Can I use it on both my Mac and PC with the same data?** Not yet — each installation is currently independent (see [Limitations](#limitations)). An Android companion app exists separately with its own sync story; see `docs/SYNC.md` if you're building from source.

## Limitations

Read honestly, not softened:

- **Unsigned builds.** No Apple Developer ID or Windows code-signing certificate is configured yet, so both installers trigger a one-time OS warning (see [Installing](#installing)). The apps themselves aren't doing anything the warning implies is dangerous — they're just unidentified to Gatekeeper/SmartScreen.
- **No cross-device sync between the desktop builds.** A macOS install and a Windows install (or two separate installs on the same OS) each have their own independent database.
- **Windows build has had less real-world runtime than macOS.** The Windows packaging pipeline is validated by CI (build + backend health check) rather than by hand on physical Windows hardware during development, since none was available.
- **No auto-update.** Getting a new version means downloading the new installer from Releases and running it again — your data is preserved automatically, but nothing prompts you when a new version ships yet.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the backend, Android app, and desktop wrappers fit together
- [`docs/DATABASE.md`](docs/DATABASE.md) — schema conventions, money handling, backups
- [`docs/FINANCE.md`](docs/FINANCE.md) / [`docs/FINANCE_V2.md`](docs/FINANCE_V2.md) — transactions, transfers, accounts vs. funds
- [`docs/STUDY_ENGINE.md`](docs/STUDY_ENGINE.md) — the event-sourced focus timer, streaks, statistics
- [`docs/SYNC.md`](docs/SYNC.md) — the Android companion app's push/pull, conflict handling
- [`docs/DEVICES.md`](docs/DEVICES.md) — QR pairing, tokens, revocation
- [`docs/SECURITY.md`](docs/SECURITY.md) — auth, secrets, logging, known gaps
- [`docs/UI_DESIGN.md`](docs/UI_DESIGN.md) — the design system, tokens, layout conventions
- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — how to actually use the thing

## Privacy

Data is stored locally on your own computer. There is no LIFEOS account, no LIFEOS cloud database, and nothing here calls out to a third-party analytics or crash-reporting service. The only network traffic the *source* project generates elsewhere is between your own Mac and your own Android phone on your own local network, if you build and pair the separate Android companion app — the desktop builds distributed here make no network requests at all beyond the OS's own installer/update-check dialogs.

---

## Development

The rest of this README is for people building LIFEOS from source, not for normal users — see [Download LIFEOS](#download-lifeos) above if that's what you want.

### What's here

```
backend/    Django + DRF + SQLite — the server and the source of truth
android/    Native Kotlin/Compose companion app, Room-backed, offline-first
desktop/    Native desktop wrappers — LIFEOSLauncher/ (Swift, macOS), windows/ (Python + pywebview)
packaging/  Distributable-build scripts and installer definitions (macOS .dmg, Windows .exe)
scripts/    Local dev setup / start / stop / build / backup / restore
docs/       Architecture, database, finance, study engine, sync, devices, security, UI design, user guide
data/       Local application data (dev checkout only — a packaged install uses its OS app-data directory instead)
backups/    Local database backups (dev checkout only; never committed, never uploaded)
```

### Running from source (Mac)

```bash
scripts/setup_mac.sh      # one-time: venv, dependencies, migrations
scripts/build_mac_app.sh  # builds a THIN dev-mode desktop/LIFEOS.app (uses this checkout's own .venv)
open desktop/LIFEOS.app
```

That's the *dev* build — it shells out to this checkout's own `backend/` + `.venv/`, not a self-contained bundle. For development, `scripts/start_lifeos.sh` runs the backend in the foreground without building the app, and `cd backend && python manage.py runserver` (with `.venv` activated) gives you Django's autoreloading dev server.

To build the actual **distributable** `.dmg` (a fully self-contained app with Python/Django embedded — what Releases ships), see `packaging/macos/build_release.sh`.

### Running from source (Windows)

There's no dev-mode Windows wrapper (Windows doesn't need one — `python manage.py runserver` works the same as anywhere else). To build the distributable installer, see `packaging/windows/build_release.ps1` (must run on Windows).

### Android

```bash
scripts/build_android.sh
```

Produces a debug APK at `android/app/build/outputs/apk/debug/app-debug.apk`. Install it (`adb install -r <path>`, or open `android/` in Android Studio) and pair it with a from-source Mac checkout from Devices → Pair New Device — see `docs/DEVICES.md`. Not part of this distribution (see `docs/ARCHITECTURE.md`); the Android app isn't published as an APK release.

### Database & backups (dev checkout)

A from-source checkout's database is a single SQLite file at `backend/lifeos.sqlite3` (never committed — see `.gitignore`). `scripts/backup_database.sh` makes a timestamped copy under `backups/`; `scripts/restore_backup.sh [filename]` restores one. A *packaged* install instead uses its OS app-data directory — see `docs/DATABASE.md`.

### Testing

```bash
cd backend && python manage.py check && python manage.py test
cd android && ./gradlew testDebugUnitTest
scripts/check_repo_safety.py   # confirms no database/secret/backup file is tracked
```

### Repository safety

This repository must never contain a real database, `.env`, backup, or secret file — see `docs/SECURITY.md` and `scripts/check_repo_safety.py`, which CI runs on every push. If you're building on top of this project and adding your own real data for local development, keep it inside the already-gitignored paths (`backend/lifeos.sqlite3`, `backups/`, `data/`, `.env`).

### Contributing

See `CONTRIBUTING.md`.
