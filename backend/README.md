# LIFEOS Backend

Django + Django REST Framework + SQLite. See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for the full picture; this file covers just what's needed to work on the backend directly.

## Setup

```bash
cd ..
scripts/setup_mac.sh
```

Or by hand:

```bash
python3.12 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
../.venv/bin/python manage.py migrate
```

## Running

```bash
../.venv/bin/python manage.py runserver 0.0.0.0:8420   # dev server, autoreload
../.venv/bin/python run_server.py                        # waitress — what LIFEOS.app actually runs
```

Note the two are not equivalent for static files: `runserver` serves them automatically in `DEBUG` mode; `run_server.py` relies on the `WhiteNoise` middleware configured in `lifeos/settings.py` (see the comment there) because `waitress` has no such built-in behavior. If you add a new static asset and it 404s under `run_server.py` but works under `runserver`, that middleware is what to check first.

## Apps

One Django app per domain under `apps/` — `core`, `devices`, `people`, `school`, `projects`, `tasks`, `finance`, `study`, `calendar_app`, `journal`, `writing`, `goals`, `notes`, `inbox`, `dashboard`, `sync`, `security`, `search`. See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md#backend-app-layout) for what each owns.

## Tests

```bash
../.venv/bin/python manage.py test
```

147 tests as of this build, covering every app. `apps/finance/tests.py` and `apps/study/tests.py` are the deepest — see [`../docs/FINANCE.md`](../docs/FINANCE.md) and [`../docs/STUDY_ENGINE.md`](../docs/STUDY_ENGINE.md).

## Demo data

`python manage.py seed_ui_demo` populates clearly fictional sample data (courses, study sessions, projects, people, accounts, transactions, journal, writing) for visually reviewing the UI. Development only — never runs automatically, and refuses to run before first-run setup has created a profile.

## Environment

No `.env` file is required for normal use — `SECRET_KEY` is auto-generated and cached locally on first run if not otherwise supplied. See `.env.example` for the variables that *can* be set (default currency, timezone, debug mode, custom DB path) if you want to override the defaults.
