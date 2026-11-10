# CADEN (Centralized Application Device Enforcement Network)

CADEN is a lightweight, stealthy, and robust licensing and governance engine designed for web-based applications. It provides offline-first trial management, hardware fingerprinting, real-time telemetry, and remote administrative control via a secure dashboard and Telegram bot integration.

## Key Features
- **Offline-First Trial Management**: Grants configurable trial periods even without internet, requiring online activation before expiry.
- **Hardware Fingerprinting**: Generates a unique, persistent Device ID based on canvas hashing and browser characteristics.
- **Stealth Telemetry**: Buffers logs locally and discharges them silently when online.
- **Remote Governance**: Real-time WebSocket control for immediate license revocation or extension.
- **Telegram Integration**: Instant notifications and inline action buttons (Extend 7/30/365 Days, Revoke, Approve Appeals) directly from Telegram.
- **Revocation Appeal Workflow**: Allows revoked users to submit updated contact details for admin review.

## Project Structure
- `backend/`: FastAPI server handling licensing, telemetry, and webhook endpoints.
- `frontend/`: Static HTML/JS dashboard for administration.
- `docker-compose.yml`: Container orchestration for the CADEN engine.

## Quick Start
1. Ensure `.env` contains valid `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
2. Run `docker compose up -d --build`.
3. Access the dashboard at `http://localhost:8000`.
4. Default Admin Credentials: `admin` / `admin123` (Change immediately via the dashboard).

## Client Integration (For App Developers)
To protect your application, include the following CSS snippet in the `<head>` of your `index.html` to prevent flash of unlicensed content:
```html
<style> body { opacity: 0; transition: opacity 0.3s ease-in; } </style>
```

Then, inject the full CADEN client script (provided below) before the closing `</head>` tag.

### caden_script.txt (v0.6.2)
```html
<!-- caden_script.txt not found in expected directory. Please paste v0.6.2 here manually. -->
```
