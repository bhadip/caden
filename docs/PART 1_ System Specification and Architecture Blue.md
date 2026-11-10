# A. SYSTEM REQUIREMENTS SPECIFICATION (SRS)

## 1. Functional Requirements

### 1.1 Local Grace Period & Installation Experience
- **Zero-Prompt First Boot**: The client application must load immediately on a user's machine via the `file://` protocol from an unzipped directory without requiring active license registration or network validation.
- **Configurable Grace Period Window**: The system must allow users uninterrupted access to the dashboard for a custom duration configured globally or per-app on the server database.
- **Local Activation Generation**: On first boot, the system must securely read and log a local timestamp to establish the client creation event.

### 1.2 Multi-Tenant Application Governance
- **App Isolation**: The system must independently register and govern multiple disparate applications (e.g., `RCM_DASHBOARD`, `FUTURE_APP_A`) sharing the same centralized license manager backend.
- **Unique Namespacing**: Licensing, structural arrays, and analytics logs saved on the browser must be securely separated using explicit application-ID prefixes.

### 1.3 Device Fingerprinting & Binding
- **Hybrid Hardware Attestation**: The system collects device-specific browser attributes (Canvas profile, CPU layout, screen resolution) to compute a deterministic hardware fingerprint string. 
- **Persistent UUID Fallback**: To prevent false-positive lockouts due to browser updates or privacy modes altering canvas data, the system generates a persistent, random UUID on first boot. The final device ID is a hash of both the hardware fingerprint and this persistent UUID, ensuring continuity for legitimate users.
- **Strict Correlation**: A license token must only grant validation clearances if the requesting machine's runtime fingerprint strictly matches the server-signed token values.

### 1.4 Administration & Lifecycles (Web + Telegram)
- **Primary Web Administration Dashboard**: A secure, responsive web application for administrators to manage application registrations, issue/revoke licenses, configure grace periods, and query/view synchronized telemetry logs.
- **Telegram Integration Engine**: The server uses the Telegram Bot API to stream real-time push alerts regarding expiring grace periods or standard tokens. 
- **Interactive Telegram Renewals**: The administrative interface supports mobile inline buttons, allowing admins to instantly approve license renewal requests (e.g., 30 days, 90 days, lifetime) or execute real-time revocation commands directly from the chat.

### 1.5 Offline Performance Analytics & Diagnostic Vault
- **Multi-Level Telemetry Logging**: The client supports configurable log levels defined in `CADEN_CONFIG`:
  - **Level 1 (Critical)**: App/data errors, runtime exceptions, tamper alerts, and revocation events.
  - **Level 2 (Operations - Default)**: Includes Level 1, plus timestamps of user access, specific operations, and record-saving events.
- **Local Catching Queue**: Intercept and queue all JavaScript unhandled errors and structural lifecycle milestones while fully disconnected.
- **Silent Upstream Synchronization**: The client continuously monitors browser connectivity and transparently offloads accumulated JSON telemetry to the server via compressed, background payloads only when internet access becomes available.

## 2. Non-Functional Requirements

### 2.1 Security & Communication Stealth
- **Zero-File Ingress Profile**: Integration must not introduce auxiliary configuration or system files to the application distribution package. All configuration properties must be embedded inside the existing structure.
- **Stealth WebSocket Encapsulation**: Establish client-to-server validation check-ins using TLS-encrypted WebSockets (`wss://` over port 443) to mask system signals as ordinary internet socket traffic, avoiding firewall detection.

### 2.2 Integrity & Tamper Resilience (Layman Explanation)
- **Military-Grade Asymmetric Cryptography**: Think of the license like a sealed, tamper-proof banknote. The CADEN server (the bank) prints it using a secret, military-grade stamp (RSA-2048/4096 Private Key, RS256 algorithm). The client app (the cashier) verifies the stamp's authenticity using a public guide (Public Key). Because the secret stamp *never* leaves the server, it is computationally infeasible for a user to forge a valid license. The app will only run if the server explicitly authorized it.
- **Anti-Clock-Skew Defences**: The application automatically restricts operations if it detects the system runtime clock has been backdated behind the historic timeline recorded in local storage arrays.

---

# B. ARCHITECTURE & DESIGN DOCUMENT (ADD)

## 1. Architectural Design Overview
The system employs an offline-first distributed model, comprising a central Python-driven Linux node, a secure external push notification network, a web-based admin dashboard, and a decoupled client-side environment running directly out of the browser's local sandbox profile.

+-----------------------------------------------------------------------------------+
 |                            CADEN ENGINE CORE                                      |
 +-----------------------------------------------------------------------------------+
      [ WEB CLIENT SIDE ]       [ DEBIAN SERVER ]        [ WEB ADMIN ]    [ MOBILE ADMIN ]
  +--------------------------+  +-----------------------+  +------------+  +----------------+
  | Index.html Runtime Context|  | FastAPI Engine        |  | Dashboard  |  | Telegram Client|
  |                          |  |                       |  | UI         |  |                |
  |  +--------------------+  |  |  +-----------------+  |  |            |  |  +----------+  |
  |  | LocalStorage Vault |  |  |  | SQLite DB       |  |  | - Licenses |  |  | Approval |  |
  |  | - License Tokens   |  |  |  | App Registries  |  |  | - Logs     |  |  | Interface|  |
  |  | - Telemetry Logs   |  |  |  | Device Mapping  |  |  | - Configs  |  |  +----------+  |
  |  +--------------------+  |  |  +-----------------+  |  +------------+  +----------------+
  |                          |  |                       |         ^               ^
  |  +--------------------+  |  |  +-----------------+  |         | HTTPS         | Webhook/
  |  | SubtleCrypto Engine|  |  |  | Cryptography Key|  |         +---------------+ API
  |  | - Token Assure     |  |  |  | Store (RS256)   |  |
  |  +--------------------+  |  |  +-----------------+  |
  +--------------------------+  +-----------------------+

## 2. Database Schema Blueprint (SQLite)
                       +-------------------+
                        |   APPLICATIONS    |
                        +-------------------+
                        | id (PK, VARCHAR)  |
                        | name              |
                        | grace_days        |
                        +-------------------+
                                  |
                                  | 1
                                  |
                                  | 0..*
                        +-------------------+
                        |     LICENSES      |
                        +-------------------+
                        | id (PK, INT)      |
                        | app_id (FK)       |
                        | device_id         |
                        | owner_name        |
                        | status            |
                        | first_boot_at     |
                        | expires_at        |
                        +-------------------+
                                  |
                                  | 1
                                  |
                                  | 0..*
                        +-------------------+
                        |   UNIFIED_LOGS    |
                        +-------------------+
                        | id (PK, INT)      |
                        | app_id (FK)       |
                        | device_id         |
                        | log_level (INT)   | <-- 1=Critical, 2=Operations
                        | log_type          |
                        | payload (JSON)    |
                        | created_at        |
                        +-------------------+
                                  |
                                  | 1
                                  |
                                  | 0..*
                        +-------------------+
                        |   ADMIN_USERS     |
                        +-------------------+
                        | id (PK, INT)      |
                        | username          |
                        | password_hash     |
                        | role              |
                        +-------------------+

## 3. Procedural Sequence Flows

### 3.1 Initial Launch and Grace Attribution Sequence
Client Browser               Storage Sandbox               Debian Licensing Node
       |                             |                                 |
       | 1. Launch index.html        |                                 |
       |---------------------------->|                                 |
       |                             |                                 |
       | 2. Check local parameters   |                                 |
       |---------------------------->|                                 |
       |                             |                                 |
       | 3. Parameter status: NULL   |                                 |
       |                             |                                 |
       | 4. Generate Persistent UUID + Hardware Fingerprint            |
       |                             |                                 |
       | 5. Record Initial Activation Stamp                            |
       |-------------------------------------------------------------->|
       |                             |                                 |
       |                             | 6. Save Grace Epoch Properties  |
       |                             |-------------------------------->|
       |                             |                                 |
       | 7. Grant Application Execution Access                         |
       |<--------------------------------------------------------------|

### 3.2 Real-time Remote Revocation & Kill-Switch Sequence
Mobile/Web Admin           Debian Server Core            Client Web Browser
       |                             |                                 |
       | 1. Dispatched Revoke Command|                                 |
       |---------------------------->|                                 |
       |                             |                                 |
       |                             | 2. Alter status to 'REVOKED'    |
       |                             |------------------>[DB]          |
       |                             |                                 |
       |                             | 3. Issue WSS Kill Instruction   |
       |                             |================================>|
       |                             |                                 |
       |                             |                                 | 4. Wipe Local Tokens
       |                             |                                 | ------------+
       |                             |                                 |             |
       |                             |                                 | <-----------+
       |                             |                                 |
       |                             |                                 | 5. Lock UI Canvas
       |                             |                                 | ------------+
       |                             |                                 |             |
       |                             |                                 | <-----------+

## 4. Technical Strategy Decisions

### 4.1 When & How to Enforce System Cessation
- **Online Enforcements**: Upon receipt of an invalid check-in status or direct `KILL` notification via the WebSocket layer, the client logic must execute an internal storage purge, suspend updates to the UI, and replace the workspace view with a locked error block.
- **Offline Enforcements**: When a user launches the application entirely disconnected, the initialization script evaluates the current system date against the embedded expiration property of the cryptographically signed local token. If the system clock passes this deadline, initialization halts before any functional components render.
- **User Session Protection Safeguard**: To protect user workflows, the system will not disrupt active input mid-session if it detects an invalid check-in status or license expiration. Instead, the runtime engine will run an automated backup of all locally changed values into an encrypted storage block within `localStorage`, disable any outward data export buttons, and display a modal informing the user that their offline operational profile has expired.

### 4.2 Anti-Clock-Skew Validation Engine
To protect against intentional manipulation of the host system clock to extend operational parameters, the application maintains a strict chronological timeline validation loop:
1. Every runtime tracking log saved to local storage updates a parameter named `<APP_ID>_LAST_SEEN_TIMESTAMP`.
2. Upon subsequent engine loads, the validation logic compares the host machine's current system time (T_current) against the saved parameter (T_last_seen).
3. If T_current < T_last_seen, the engine immediately flags a system clock skew violation, forces the client state to expired, and demands administrative synchronization.
