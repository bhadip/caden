# CADEN Revision History

## [v0.6.2] - 2026-11-11
### Added
- **Local Revocation Persistence**: Added `KEYS.revokedStatus` to `localStorage`. Devices now remember their revoked state even when offline, preventing bypass by disconnecting the network.
- **Online/Offline Status Indicator**: Added a real-time green/grey dot to the License Management table, powered by persistent WebSocket connection tracking.

### Changed
- Unified all terminology from "Grace Days" to **"Trial Days"** across backend, frontend, and client scripts.
- Client script now waits for server response before displaying the trial deadline message, ensuring 100% accuracy with server-configured trial durations.

### Fixed
- Fixed webhook endpoint `500 Internal Server Error` by switching to FastAPI's `Request.json()` for robust payload parsing.
- Fixed `NameError: manager is not defined` by ensuring proper instantiation order in `main.py`.
- Resolved syntax errors caused by fragile string replacements by implementing bulletproof Regex-based patching.

## [v0.5.0 - v0.6.1] 
- Implemented Revocation Appeal workflow with change-highlighting (pencil emoji removed for cleaner UI).
- Added configurable Trial Days and Reminder Days via Dashboard Config.
- Integrated Telegram inline buttons (Extend 7/30/365 Days, Revoke, Reactivate, Approve/Deny Appeal).
- Forced server timezone (Asia/Singapore) for all Telegram expiry notifications.
- Added Device ID display under the "Protected by CADEN" badge.

## [v0.1.0 - v0.4.0]
- Initial CADEN engine setup with JWT licensing, canvas fingerprinting, and basic telemetry.
- Added Admin Dashboard with License, Log, and Device Profile management.
- Implemented Trash Bin for telemetry logs.
