# Sync

## Architecture

Sync is push-then-pull, run by a WorkManager `CoroutineWorker` (`android/.../sync/SyncWorker.kt`) on a 15-minute periodic schedule (WorkManager's floor for periodic work) plus an immediate one-off run right after pairing and on manual "Sync now."

1. **Push**: drain `sync_queue` (a local Room table — one row per pending local create/update, written by each repository's mutating methods) in creation order, calling the matching DRF endpoint for each. A row is removed from the queue only after its request succeeds; a failure leaves it queued for the next run rather than dropping it.
2. **Pull**: fetch the current state of every collection (tasks, projects, courses/topics, accounts, transactions, study sessions, journal entries) from the API and reconcile each row into Room via each repository's `applyServerX()` method.

Nothing is pushed or pulled unless the device is actually paired (`DeviceStore` has a saved `base_url` and `device_token`) — an unpaired install is a no-op sync, never an error.

## Conflict rule

**A row with a local edit still queued for push is never overwritten by a pull.** Every `applyServerX()` method checks the local row's `syncStatus` first:

```kotlin
suspend fun applyServerTask(task: TaskEntity) {
    val local = dao.getById(task.id)
    if (local != null && local.syncStatus == "pending_push") return
    dao.upsert(task.copy(syncStatus = "synced"))
}
```

This is a deliberately simple rule — "local wins until it's actually been sent" — rather than a general three-way merge. It's enough to prevent the concrete failure mode that matters most here: pausing a study session on the phone and having a slow, already-in-flight pull silently revert it back to "active" a moment later. It is *not* a full CRDT or last-write-wins-by-timestamp system, and two devices editing the *same* field of the *same* record while both offline is not automatically reconciled beyond "whichever one's push lands last in the queue wins on the server" — the spec's own framing (§78) treats this as acceptable for simple entities and calls for a review UI only for higher-stakes ones (financial transactions, journal, study history). A dedicated conflict-review screen is not yet built; today those entity types get the same "local pending-push wins" protection as everything else, which prevents silent data loss but doesn't yet surface an explicit merge UI when both sides genuinely diverged.

## What syncs

Tasks, Projects, Courses/Topics, Accounts, Transactions, Study Sessions (and their events), Journal Entries. People, Notes, Goals, and Calendar Events have Room entities and DAOs ready (`android/.../data/local/entities/`) but are not yet included in `SyncWorker`'s pull list — see the Known Limitations note in the root README rather than assuming they sync today.

## Active session across devices

There is exactly one "active session" concept, read the same way regardless of which device asks (`apps.study.services.active_session()` on the backend; the equivalent Room query on Android). A session started on Android and synced to the Mac is the *same* row on both sides, not a duplicate — the Mac's Study screen and Android's Study screen both resolve to whichever session has `status IN (active, paused)` most recently, and pause/resume/finish events append to that one row's event log no matter which device sends them.

## Transport

Android reaches the Mac directly over the LAN — `http://<mac-lan-ip>:8420/`. There is no cloud relay, no message broker, and no server component beyond the same Django/DRF instance the desktop UI talks to. `DynamicBaseUrlInterceptor` (`android/.../data/remote/NetworkModule.kt`) rewrites every outgoing request's host/port to whatever `DeviceStore` currently holds, since the Mac's IP is discovered once at pairing time (via the QR code, which encodes the current LAN IP — see `docs/DEVICES.md`) and can legitimately change later (DHCP lease renewal, network switch). There is currently no automatic re-discovery if the IP changes after pairing; re-pairing (scanning a fresh QR code) is the recovery path. A manual "enter IP" fallback for cases where QR scanning itself isn't viable is not yet built.

## Verification status

Verified end-to-end in this build: the pairing handshake (`claim_device`) issuing a real device token and the Android app successfully authenticating subsequent requests with it (tested by simulating the exact request the Android client sends). The full periodic sync loop's push/pull logic is implemented and unit-tested at the repository level, and the Android project builds and its own unit tests pass, but running the *complete* bidirectional loop against a live Android emulator or device was not possible in this environment (no emulator was available to boot — see the root README's Testing section for exactly what was and wasn't run). The code path is the same one exercised by the pairing test, so the remaining gap is specifically "watch two live devices reconcile a change," not "does the request-building/parsing logic work."
