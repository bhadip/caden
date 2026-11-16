# CADEN Engine Changelog

## v0.6.12 (2026-11-17)
### Backend
- **CORS Enabled**: Added `CORSMiddleware` to allow requests from all origins (including `file://` and `localhost`).
- **JWT Fix**: Fixed 500 Internal Server Error by ensuring JWT `exp` and `iat` claims use integer Unix timestamps.
- **DB Connection Fix**: Fixed `sqlite3.ProgrammingError` by ensuring database updates commit before connection closes.
- **Self-Healing Upsert**: `/v1/activate` now upserts `ownerName`, `ownerEmail`, and `ownerWhatsapp` from the request body, ensuring typed identity survives client-side merge.
- **Online Status Tracking**: Added `last_seen_at` column to `LICENSES` table. `/v1/activate` and `/v1/profile` endpoints now stamp this timestamp.

### Frontend (Admin Dashboard)
- **Online Dot Logic**: Replaced WebSocket-based online check with `last_seen_at` database timestamp (5-minute window).
- **Timezone Fix**: Fixed UTC parsing for `last_seen_at` to prevent false "Offline" status due to local timezone misinterpretation.

### Client Script (caden_script.txt)
- **Offline-First**: Registration saves to `localStorage` before network call; fails open if server unreachable.
- **Store-and-Forward**: Background engine retries pending registration on `online` event and every 5 minutes.
- **Guaranteed Heartbeat**: `syncProfile()` now called unconditionally on every online page load, independent of activation path.
- **Hardened Merge**: `autoActivate()` and `attemptPendingRegistration()` explicitly merge server owner fields without wiping local data.
- **Trial Fallback**: Default offline trial period increased from 3 days to 7 days.
