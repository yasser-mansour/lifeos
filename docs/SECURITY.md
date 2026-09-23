# Security

## Threat model

LIFEOS is not internet-facing. It listens on the Mac's LAN interface so Android can reach it, but there is no port forwarding, no public DNS, and no cloud relay — the realistic threat is someone else on the same Wi-Fi network, not the open internet. Every design decision below follows from that.

## Authentication

- **Desktop UI**: one owner account (`django.contrib.auth.User`, created at first-run), session-authenticated. The login screen only ever asks for a passcode — the username is fixed to `owner` and hidden, since there is exactly one user (spec §97).
- **API / Android**: per-device bearer tokens (`Authorization: Device <token>`), issued at pairing time and never transmitted again in plaintext after that (see `docs/DEVICES.md`). `DeviceTokenAuthentication` is a DRF authentication class, not Django's session auth — a device token is scoped to *that device*, independently revocable, and never doubles as a login credential for the web UI.
- The `/api/devices/claim/` endpoint is the one intentionally unauthenticated endpoint in the system, since a not-yet-paired device by definition has no credential yet. It's protected instead by the short-lived, single-use `PairingToken` (see `docs/DEVICES.md`) — the closest thing to "authentication" an unpaired device can present.

## CSRF

Django's CSRF middleware is on for every session-authenticated (desktop) request; `static/js/app.js`'s `apiFetch()` helper attaches the CSRF token to every fetch automatically. DRF endpoints authenticated via `DeviceTokenAuthentication` are exempt from CSRF the normal DRF way (CSRF is a browser-session concept; a device bearer token isn't a cookie, so it isn't vulnerable to the same cross-site attack CSRF protection defends against).

## Secrets

- `SECRET_KEY` is never hardcoded. If not supplied via environment, `backend/lifeos/settings.py` generates one on first run and caches it in `backend/.secret_key` (gitignored, `chmod 600`).
- The field-encryption key used by `apps/security/crypto.py` (see below) is read from the macOS Keychain (`security find-generic-password`) or generated and stored there on first use (`security add-generic-password`). This is a real gap on Windows — see Known gaps below.
- Nothing under `backend/` that could contain real data — the database file, the secret key, backups, media uploads — is committed. See the root `.gitignore`, and `scripts/check_repo_safety.py` (run by CI on every push) as a second line of defense against ever accidentally tracking one.

## App-data location (distributed builds)

A packaged install (the macOS `.dmg` or Windows installer from Releases) never stores the database, secret key, backups, or logs inside the installed application itself — an app update or reinstall must never risk that data. `desktop/LIFEOSLauncher/BackendManager.swift` (macOS) and `desktop/windows/lifeos_windows.py` (Windows) each set `LIFEOS_APP_DATA_DIR` to the OS's own per-user application-data directory (`~/Library/Application Support/LIFEOS` / `%LOCALAPPDATA%\LIFEOS`) before starting the backend; `backend/lifeos/settings.py` derives the database path, `.secret_key`, `data/`, `media/`, and `backups/` from that one variable when it's set. A from-source dev checkout never sets it, so nothing changes for existing local development — see `docs/DATABASE.md`.

## Logging

`LOGGING` in `settings.py` is deliberately minimal: level and path only, no request/response body logging. `core.ActivityEvent` (the in-app activity feed) never stores card numbers, tokens, or full message/journal content — only a short human-readable verb (e.g. "Added transaction", not the transaction's actual amount or description).

## Cards

`finance.Card` stores nickname, linked account, last 4 digits, type, and expiry — nothing that can be used to actually charge the card. No CVV, PIN, online-banking password, OTP, or recovery code field exists anywhere in the schema, and none is ever logged. Full card number storage was considered and deliberately **not implemented** — spec §41 explicitly permits omitting it rather than doing it insecurely, and doing it correctly (encrypted at rest, key in the Keychain, never exposed via a list endpoint, deliberate reveal-only access) was judged not to fit alongside everything else in this build's scope. See `docs/FINANCE.md`.

## Field encryption (built, not yet used)

`apps/security/crypto.py` implements `encrypt_field()`/`decrypt_field()` using `cryptography`'s Fernet (AES-128-CBC + HMAC) with a key sourced from the macOS Keychain as described above. No model currently has a field that needs it — it exists so that if one is added later, the correct pattern (key never in source control, never in the database, never logged) is already in place and easy to reach for.

## Backups

Backups are plain copies of the live (unencrypted) SQLite database, written to `backups/` (gitignored) and never uploaded anywhere automatically (spec §93). Since they contain the same data as the live database, they should be treated with the same care — e.g., if you ever back up this Mac itself to an external drive or cloud service, be aware `backups/*.sqlite3` will go with it unless excluded.

## Distribution signing status

Neither the macOS `.dmg` nor the Windows installer is code-signed (no Apple Developer ID or Windows code-signing certificate is configured). Both are built and shipped anyway, honestly labeled as an unsigned beta — see the README's Installing section for exactly what warning a user sees and why disabling Gatekeeper/SmartScreen globally is never the right answer to it.

## Known gaps

- **No Windows equivalent of the macOS Keychain for the field-encryption key.** `apps/security/crypto.py` currently only has a real secure-storage path on macOS; the "non-macOS fallback" is a gitignored local file under the app-data directory. No model uses field encryption yet (see above), so this has no current real impact, but implementing a Windows DPAPI-backed path is the right fix before any field actually needs it there.
- No automated `pip-audit`/dependency vulnerability scan is wired into CI yet (CI itself — safety scan + backend tests, and macOS/Windows packaging smoke tests on release — was added as part of the distribution work; see `.github/workflows/`).
- No rate limiting on the login or claim-device endpoints. On a trusted LAN with a short-lived, single-use pairing token this was judged acceptable for v1; it would be a reasonable hardening item if this were ever exposed beyond a home network.
