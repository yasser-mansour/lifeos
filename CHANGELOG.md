# Changelog

## 0.1.0-beta.1 — first distributable beta

First desktop distribution of LIFEOS: a macOS `.dmg` and a Windows installer, each a self-contained app with no Python/Django/dependency installation required.

- Tasks, Focus, Projects, Finance (personal and business, Accounts vs. Funds), People & Organizations, Notes, School, Journal, Writing, Calendar, Goals
- First-run setup: name, passcode, choose which modules to use, optional Finance/School/Project setup
- Local backups (create/list/restore) from Settings
- Each installation's data is local and independent — no account, no server

### Known limitations
- Unsigned builds on both platforms (no code-signing certificate configured yet) — see the README's Installing section for the exact first-launch warning and what to do about it.
- No sync between separate desktop installations, and no auto-update mechanism yet.
