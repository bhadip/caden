# CADEN Licensing & Governance - Revision History

## CADEN Script (`caden_script.txt`)
- **v0.6.30:** Unify email validation in online registration form (require '@'), matching the offline fallback.
- **v0.6.29:** Full clean rewrite to fix duplicated/mangled "Revoked License" blocks and broken IIFE that crashed the JS parser (white screen).
- **v0.6.28:** Isolated `revealApp()` to only hide modal and dispatch `CADEN_READY`; added empty appeal form for revoked licenses.
- **v0.6.27:** Calculate & save local 30-day trial expiry on offline first-run registration.
- **v0.6.26:** Fix malformed IIFE closure at end of file.
- **v0.6.25:** Replace static revoked block with dynamic empty appeal form.
- **v0.6.24:** Hard block for `REVOKED` status.
- **v0.6.23:** Persist `expires_at` in `userInfo` merge across all paths (initial, offline sync, poller).
- **v0.6.22:** Unify key names in poller merge (`.name` instead of `.owner_name`).
- **v0.6.21:** Add `RCM_EXPIRES_AT` and `RCM_TOKEN` dedicated localStorage keys.
- **v0.6.20:** Strip HTML wrappers to serve pure JS from the server endpoint.
- **v0.6.19:** Offline-first UX hooks, local expiry calculation, license status exposure.
- **v0.6.18:** Admin-owner poller uses POST (was GET -> 404).
- **v0.6.17:** Force localStorage & UI update on `autoActivate`.
- **v0.6.16:** Expose IIFE internals to `window` scope for out-of-scope pollers.
- **v0.6.15:** Admin-owner propagation poller + navigation telemetry.
- **v0.6.14:** Activity heartbeat scope fix + admin priority on heartbeats.
- **v0.6.13:** Initial integration build.

## CADEN Loader (`caden_loader.txt`)
- **v1.3:** DOM timing fix (`setTimeout`) + idempotency check to prevent data wipe on cold-start offline reload.
- **v1.2:** Embedded minimal cold-start fallback for true offline-first first launch.
- **v1.1:** Added `window.CADEN_LOADED = true` flag.
- **v1.0:** Initial loader with `no-store` cache fetching.

## Backend & Infrastructure
- Added `GET /caden_script.txt` endpoint with `Cache-Control: no-store`.
- Removed `allow_credentials=True` from CORS to fix `file://` (Origin: null).
- Fixed SQLite binding error in `/v1/activate` (7 bindings for 4 placeholders).
- Enforced Admin priority: heartbeats only update `last_seen_at`.
