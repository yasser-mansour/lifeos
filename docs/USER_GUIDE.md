# LIFEOS User Guide

## First launch

Open `LIFEOS.app`. It starts the backend automatically (you'll briefly see "Starting LIFEOS…"), then the first-run screen asks for your name, a passcode (protects the app on this Mac — nothing is sent anywhere), default currency, theme, and optionally your school name. After that you're in.

Day to day, your session stays signed in — you won't see the passcode screen again unless you explicitly log out or the Mac hasn't opened LIFEOS in a long time.

## Daily use

- **`Cmd+K`** anywhere opens the command palette — search across everything, or jump straight to an action (Start Focus, Add Transaction, New Task, …).
- **Quick Add** (top of Home) opens the same set of fast-creation actions.
- **Inbox** is for anything you don't want to think about right now — type it and decide later whether it's a task, a note, or nothing.

## Study

Study → Start Focus → optionally pick a course/topic/task, choose Stopwatch, Countdown, or Pomodoro, and go. The active-session screen is intentionally quiet — just the timer, Pause/Finish, and a Cancel-if-you-need-to link. Your history, statistics, and heatmap all update from real sessions as you go; nothing there is sample data once you've studied at least once.

## Finance

Finance → Add Account for each bank/cash/savings account you want to track (personal and business are separate contexts, always). Add Transaction is deliberately fast — amount, type, account, category, description, date; everything else (project, person, tags, notes) is under "More options". For a payment that covers multiple months (rent paid in advance) or multiple categories, check "Split into allocations" — the amount that actually left your account today doesn't change, only how it's reported.

Transfers between your own accounts (personal bank → cash, business → personal) use the dedicated Transfer flow, not a regular transaction — that's what keeps them out of your income/expense totals.

## Pairing your Android phone

Devices → Pair New Device shows a QR code. Open LIFEOS on your phone, go to Devices → Pair with Mac, and scan it — both devices need to be on the same Wi-Fi network. The code expires after two minutes; if it does, just generate a new one. Once paired, your phone syncs automatically in the background, and works normally (offline, using its own local data) whenever the Mac isn't reachable.

## Backup & restore

Settings → Backup → Create Backup makes a timestamped copy of your entire database under `backups/` on this Mac. Nothing is ever uploaded anywhere. To restore an older backup, click Restore next to it — LIFEOS automatically saves a safety copy of your *current* data first, so restoring is never a one-way door.

## Export

Settings → Export gives you JSON or CSV for each major dataset (accounts, transactions, study sessions, tasks, projects, journal, writing, goals) — your data, in a format you can open in a spreadsheet or take somewhere else.

## Appearance

Settings → Appearance: Light, Dark, or System. Android has the same three options under its own Settings tab, set independently per device.

## If something looks wrong

- The health check LIFEOS.app waits on is `http://127.0.0.1:8420/api/health/` — if the app seems stuck on "Starting LIFEOS…", check `data/logs/backend.log` for what the backend printed on startup.
- Closing the LIFEOS window quits the app (and stops the backend with it) — reopen it from the Dock or Applications the normal way.
- If Android says it can't reach the Mac, confirm both devices are on the same network and re-pair (the Mac's IP can change between networks).
