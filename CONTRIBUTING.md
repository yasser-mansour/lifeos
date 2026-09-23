# Contributing to LIFEOS

This started as a personal, single-user project and is now distributed so a few friends can run their own independent copies (see the README). It isn't yet organized as an open-source project looking for outside contributions — there's no chosen license yet (see below), and the architecture docs in `docs/` describe one specific person's real-life setup more than a general-purpose product.

If you'd still like to poke at the source: `docs/ARCHITECTURE.md` is the best starting point, `scripts/setup_mac.sh` gets a dev checkout running, and `cd backend && python manage.py test` is the test suite. Please don't open pull requests against this repository for now — file an issue first if you've found something worth fixing (a real bug, a security concern, a build failure), and it'll go from there.

## Reporting a security issue

See `SECURITY.md` — please don't open a public issue for anything that looks like a real vulnerability.

## Code style

Match what's already there: Django app-per-domain under `backend/apps/`, business logic in each app's `services.py` rather than in views/templates, Kotlin/Compose conventions in `android/` mirrored from the existing screens. No enforced linter yet beyond what CI runs (`manage.py check`, `manage.py test`, `scripts/check_repo_safety.py`).
