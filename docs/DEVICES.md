# Devices & Pairing

## Model

- **`Device`** — one row per paired device (the Mac itself is registered as a `primary` device the first time `study` records a session from it; Android devices are created at claim time). Tracks platform, model, `last_seen`, `last_sync`, `status`, and `revoked`.
- **`DeviceCredential`** — the long-lived bearer token a device uses on every request after pairing. Only a SHA-256 hash is stored (`DeviceCredential.issue()` returns the raw token exactly once, at pairing time, the same way the backend never stores plaintext passwords). Re-issuing a credential for a device immediately invalidates its previous token.
- **`PairingToken`** — a short-lived (120 second), single-use token embedded in the Mac's QR code. It grants nothing by itself beyond "may call `/api/devices/claim/` once, before it expires, to receive a real `DeviceCredential`."

## Pairing flow

1. Mac: Devices → Pair New Device generates a `PairingToken` and renders it as a QR code (`apps/devices/services.py::pairing_qr_data_uri`) encoding `{token, host, port, expires_at}`, where `host` is the Mac's own LAN IP (`local_lan_ip()` — a UDP-connect trick that doesn't actually send traffic, just asks the OS which local interface would be used to reach the internet, which is the same interface Android needs to reach the Mac).
2. Android: the Pairing screen's camera view (`ui/devices/PairingScreen.kt`, CameraX + ML Kit barcode scanning) decodes the QR payload and calls `POST /api/devices/claim/` with the token and some device metadata.
3. Backend: `apps/devices/api.py::claim_device` validates the token (`PairingToken.is_valid` — not already used, not expired), creates the `Device` row, issues a `DeviceCredential`, and marks the token consumed. The same token cannot be used twice, even if the request is retried (`PairingTokenTests::test_consumed_token_is_single_use` and `ClaimDeviceApiTests::test_claim_token_cannot_be_reused`).
4. Android stores the returned token in `DeviceStore` (Jetpack DataStore) and immediately triggers a sync.
5. Mac's pairing screen polls `devices:pair_status` every 2 seconds and redirects to the device list the moment the token shows as consumed — there's no separate "confirm" step on the Mac side.

## Why this design

The QR code itself is worthless after 120 seconds or one use — it is not a standing credential, so a screenshot of it (or someone glimpsing it over your shoulder) doesn't grant lasting access the way embedding the real device token in the QR would have. The *real* credential is only ever transmitted once, directly between the two devices on the LAN, immediately consumed by the backend.

## Revocation

Devices → (device row) → Revoke sets `Device.revoked = True`, deactivates its `DeviceCredential`, and any subsequent request bearing that device's old token is rejected by `DeviceTokenAuthentication` (`apps/devices/auth.py`) with 401, regardless of how "long left" the token would otherwise have had — a revoked device's credential is dead immediately, not just excluded from new pairings.

## Manual IP fallback

Not yet built. Today, re-pairing (Mac generates a new QR code, phone scans it again) is the only way to update the Mac's address on Android if it changes after the initial pairing — see the Known Limitations note in the root README.
