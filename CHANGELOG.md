# CADEN Revision History

## [Dashboard v0.5.0 & Backend v1.1.0] - 2026-11-12
### Added
- **Bulk Delete/Restore for Telemetry Logs**: Added checkboxes to select multiple logs. "Delete Selected" moves them to the Trash Bin; "Restore Selected" recovers them.
- **Enhanced Trash Bin UI**: Redesigned modal with a fixed header/footer layout. Added a total record count and a live badge showing the number of selected records for bulk restoration.
- **Select All Functionality**: Added "Select All" checkboxes for both the main Telemetry Logs view and the Trash Bin.
### Fixed
- **FastAPI 422 Error**: Fixed the `/admin/logs/bulk-action` endpoint by manually parsing the JSON body via `Request.json()`, resolving parameter mapping conflicts.

## [Dashboard v0.4.9] - 2026-11-11
### Added
- Navigation tracking: Records user's active tab and recent navigation history when errors occur, visible in telemetry logs.
- Enhanced error context: Runtime errors now include which tab/page the user was viewing.
### Fixed
- Mobile Licenses tab: Now displays as stacked cards (like Device Profiles) instead of horizontal scroll.
- Desktop filter alignment: Date range pickers now properly aligned with other filters.
- Runtime error prevention: Added undefined checks for failureModes data to prevent cascade errors when data not loaded.

## [Dashboard v0.4.8] - 2026-11-11
### Changed
- Mobile typography now ~12.5% smaller by default and scales with the device's system/browser font-size setting (percentage-based rem root + text-size-adjust:100%). Desktop unchanged.

## [Dashboard v0.4.7] - 2026-11-11
### Added
- Mobile-responsive layout: viewport meta tag + mobile-only CSS (scrollable tables, full-width modals, stacked header). Desktop UI unchanged.
- Clickable owner contacts: email opens mail client via mailto, WhatsApp opens wa.me chat. Numbers with leading 0 auto-converted to Indonesia +62.
### Fixed
- All dashboard timestamps (Telemetry Logs, Trash Bin, License Expiry) now display in CADEN server timezone (Asia/Singapore) instead of UTC.

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
