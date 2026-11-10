import os, json, sqlite3, datetime, bcrypt, asyncio, urllib.request, urllib.error, zoneinfo, urllib.parse
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

def format_server_time(dt):
    sgt = zoneinfo.ZoneInfo("Asia/Singapore")
    return dt.astimezone(sgt).strftime('%Y-%m-%d %H:%M SGT')

def get_license_buttons(device_id, is_appeal=False):
    if is_appeal:
        return {
            "inline_keyboard": [
                [{"text": "✅ Approve Appeal (+30 Days)", "callback_data": f"approve_appeal_{device_id}"}],
                [{"text": "🚫 Deny Appeal (Keep Revoked)", "callback_data": f"deny_appeal_{device_id}"}]
            ]
        }
    return {
        "inline_keyboard": [
            [{"text": "⏱️ Extend 7 Days", "callback_data": f"extend_7_{device_id}"}],
            [{"text": "🗓️ Extend 30 Days", "callback_data": f"extend_30_{device_id}"}],
            [{"text": "📅 Extend 1 Year", "callback_data": f"extend_365_{device_id}"}],
            [{"text": "🚫 Revoke Immediately", "callback_data": f"revoke_{device_id}"}]
        ]
    }

def send_telegram(message: str, reply_markup: dict = None):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠️ Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req)
        print("✅ Telegram sent successfully")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Telegram HTTP Error {e.code}: {error_body}")
    except Exception as e:
        print(f"❌ Telegram Request Error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🤖 Telegram Loaded: {bool(TG_TOKEN)} | Chat ID: {bool(TG_CHAT_ID)}", flush=True)
    if TG_TOKEN:
        webhook_url = "https://caden.prasanti.com/v1/telegram-webhook"
        url = f"https://api.telegram.org/bot{TG_TOKEN}/setWebhook?url={webhook_url}"
        try:
            print(f"🔄 Setting webhook to: {webhook_url}", flush=True)
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                print(f"✅ Telegram Webhook response: {response.read().decode('utf-8')}", flush=True)
        except Exception as e:
            print(f"❌ Failed to set webhook: {e}", flush=True)
    yield

app = FastAPI(title="CADEN Engine Core", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "caden.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS APPLICATIONS (id VARCHAR(50) PRIMARY KEY, name VARCHAR(100), trial_days INTEGER DEFAULT 3, reminder_days INTEGER DEFAULT 3);
        CREATE TABLE IF NOT EXISTS LICENSES (
            id INTEGER PRIMARY KEY AUTOINCREMENT, app_id VARCHAR(50), device_id VARCHAR(100), 
            owner_name VARCHAR(100), owner_email VARCHAR(100), owner_whatsapp VARCHAR(50),
            system_info TEXT, status VARCHAR(20) DEFAULT 'ACTIVE', first_boot_at DATETIME, expires_at DATETIME, renewal_requested_at DATETIME
        );
        CREATE TABLE IF NOT EXISTS UNIFIED_LOGS (
            id INTEGER PRIMARY KEY AUTOINCREMENT, app_id VARCHAR(50), device_id VARCHAR(100), 
            log_level INTEGER DEFAULT 2, log_type VARCHAR(50), payload TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ADMIN_USERS (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(50) UNIQUE, password_hash VARCHAR(255), role VARCHAR(20) DEFAULT 'admin');
        CREATE TABLE IF NOT EXISTS REMINDER_LOG (id INTEGER PRIMARY KEY AUTOINCREMENT, license_id INTEGER, reminded_at DATETIME, days_before INTEGER);
    """)
    for col, dtype in [("owner_email", "TEXT"), ("owner_whatsapp", "TEXT"), ("system_info", "TEXT"), ("renewal_requested_at", "TEXT"), ("is_deleted", "INTEGER DEFAULT 0"), ("reminder_days", "INTEGER DEFAULT 3")]:
        try: conn.execute(f"ALTER TABLE LICENSES ADD COLUMN {col} {dtype}")
        except: pass
    try: conn.execute("ALTER TABLE APPLICATIONS RENAME COLUMN grace_days TO trial_days")
    except: pass
    try: conn.execute("ALTER TABLE APPLICATIONS ADD COLUMN trial_days INTEGER DEFAULT 3")
    except: pass
    
    cursor = conn.execute("SELECT id FROM ADMIN_USERS WHERE username='admin'")
    if not cursor.fetchone():
        hashed_pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
        conn.execute("INSERT INTO ADMIN_USERS (username, password_hash) VALUES (?, ?)", ("admin", hashed_pw))
    cursor = conn.execute("SELECT id FROM APPLICATIONS WHERE id='RCM_DASHBOARD'")
    if not cursor.fetchone():
        conn.execute("INSERT INTO APPLICATIONS (id, name, grace_days, reminder_days) VALUES (?, ?, ?, ?)", ("RCM_DASHBOARD", "RCM Dashboard", 30, 3))
    conn.commit()
    conn.close()

init_db()

KEYS_DIR = "/app/keys"
os.makedirs(KEYS_DIR, exist_ok=True)
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "private.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "public.pem")

if not os.path.exists(PRIVATE_KEY_PATH):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()))
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))

with open(PRIVATE_KEY_PATH, "rb") as f: PRIVATE_KEY = serialization.load_pem_private_key(f.read(), password=None)
with open(PUBLIC_KEY_PATH, "rb") as f: PUBLIC_KEY = serialization.load_pem_public_key(f.read())

class TelemetryEntry(BaseModel):
    epoch: int
    level: int
    type: str
    detail: str
    device: str
    system_info: Optional[dict] = None

class TelemetryPayload(BaseModel):
    appId: str
    entries: List[TelemetryEntry]

class AdminLogin(BaseModel):
    username: str
    password: str

class RenewalRequest(BaseModel):
    deviceId: str
    name: str
    email: str
    whatsapp: str

class AssignRequest(BaseModel):
    name: str
    email: str
    whatsapp: str

class ReactivateRequest(BaseModel):
    days: int

class PasswordChangeRequest(BaseModel):
    oldPassword: str
    newPassword: str

class AppConfig(BaseModel):
    trialDays: int
    reminderDays: int

class ResetRequest(BaseModel):
    appId: str
    deviceId: str
    adminPassword: str

@app.post("/v1/activate")
async def activate_device(appId: str, deviceId: str, ownerName: str = "", ownerEmail: str = "", ownerWhatsapp: str = "", systemInfo: Optional[str] = None, background_tasks: BackgroundTasks = None):
    conn = get_db()
    app_row = conn.execute("SELECT * FROM APPLICATIONS WHERE id=?", (appId,)).fetchone()
    if not app_row: 
        conn.close()
        raise HTTPException(status_code=404, detail="App not registered")
    
    latest_lic = conn.execute("SELECT * FROM LICENSES WHERE device_id=? AND app_id=? ORDER BY id DESC LIMIT 1", (deviceId, appId)).fetchone()
    
    if latest_lic and latest_lic["status"] == "REVOKED":
        conn.close()
        raise HTTPException(status_code=403, detail="Device Revoked")
        
    if latest_lic and latest_lic["status"] == "PENDING_REVIEW":
        if ownerName or ownerEmail or ownerWhatsapp:
            conn.execute("UPDATE LICENSES SET owner_name=?, owner_email=?, owner_whatsapp=? WHERE id=?",
                         (ownerName or latest_lic["owner_name"], ownerEmail or latest_lic["owner_email"], ownerWhatsapp or latest_lic["owner_whatsapp"], latest_lic["id"]))
            conn.commit()
        conn.close()
        raise HTTPException(status_code=403, detail="APPEAL_PENDING")

    if latest_lic and latest_lic["status"] == "ACTIVE":
        if ownerName or ownerEmail or ownerWhatsapp:
            conn.execute("UPDATE LICENSES SET owner_name=?, owner_email=?, owner_whatsapp=? WHERE id=?",
                         (ownerName or latest_lic["owner_name"], ownerEmail or latest_lic["owner_email"], ownerWhatsapp or latest_lic["owner_whatsapp"], latest_lic["id"]))
            conn.commit()
        conn.close()
        return {"token": None, "status": latest_lic["status"], "message": "Already registered"}

    trial_days = app_row["trial_days"]
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now_utc + datetime.timedelta(days=trial_days)
    
    payload = {"appId": appId, "devId": deviceId, "exp": expires_at, "iat": now_utc}
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    
    conn.execute("INSERT INTO LICENSES (app_id, device_id, owner_name, owner_email, owner_whatsapp, status, first_boot_at, expires_at, system_info) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)", 
                 (appId, deviceId, ownerName or "Pending Assignment", ownerEmail, ownerWhatsapp, now_utc.isoformat(), expires_at.isoformat(), systemInfo))
    conn.commit()
    conn.close()
    
    msg = f"🟢 <b>New Device Registered</b>\n\n👤 <b>Name:</b> {ownerName or 'Unknown'}\n📧 <b>Email:</b> {ownerEmail or 'N/A'}\n📱 <b>WhatsApp:</b> {ownerWhatsapp or 'N/A'}\n🖥️ <b>Device:</b> {deviceId}\n⏰ <b>Trial Expires:</b> {format_server_time(expires_at)}"
    print(f"DEBUG: Sending Telegram for new device: {msg}")
    send_telegram(msg, get_license_buttons(deviceId))
    
    return {"token": token, "expires_at": expires_at.isoformat().replace('+00:00', 'Z'), "status": "ACTIVE", "trial_days": trial_days}

@app.post("/v1/renewal_request")
async def request_renewal(data: RenewalRequest, background_tasks: BackgroundTasks):
    conn = get_db()
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute("INSERT INTO LICENSES (app_id, device_id, owner_name, owner_email, owner_whatsapp, status, renewal_requested_at) VALUES (?, ?, ?, ?, ?, 'PENDING_REVIEW', ?)",
                 ("RCM_DASHBOARD", data.deviceId, data.name, data.email, data.whatsapp, now_utc))
    conn.commit()
    conn.close()
    background_tasks.add_task(send_telegram, f"🔄 <b>Renewal Request</b>\n\n👤 {data.name}\n📧 {data.email}\n📱 WA: {data.whatsapp}\n🖥️ Device: {data.deviceId}")
    return {"status": "success"}

@app.post("/v1/telemetry")
def ingest_telemetry(data: TelemetryPayload):
    conn = get_db()
    for entry in data.entries:
        payload_data = entry.detail
        if entry.system_info:
            payload_data = f"{entry.detail} | SYS: {json.dumps(entry.system_info)}"
        conn.execute("INSERT INTO UNIFIED_LOGS (app_id, device_id, log_level, log_type, payload) VALUES (?, ?, ?, ?, ?)", 
                     (data.appId, entry.device, entry.level, entry.type, payload_data))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/v1/authorize-reset")
def authorize_reset(data: ResetRequest):
    conn = get_db()
    admin = conn.execute("SELECT * FROM ADMIN_USERS WHERE username='admin'").fetchone()
    if not admin or not bcrypt.checkpw(data.adminPassword.encode("utf-8"), admin["password_hash"].encode("utf-8")):
        conn.close()
        return {"authorized": False}
    conn.execute("UPDATE LICENSES SET status='RESET_PENDING' WHERE device_id=? AND app_id=?", (data.deviceId, data.appId))
    conn.commit()
    conn.close()
    return {"authorized": True}

@app.post("/v1/appeal-revocation")
async def appeal_revocation(appId: str, deviceId: str, ownerName: str, ownerEmail: str, ownerWhatsapp: str):
    conn = get_db()
    latest_lic = conn.execute("SELECT * FROM LICENSES WHERE device_id=? AND app_id=? AND status='REVOKED' ORDER BY id DESC LIMIT 1", (deviceId, appId)).fetchone()
    if not latest_lic:
        conn.close()
        raise HTTPException(status_code=404, detail="No revoked license found for this device")
    
    prev_name = latest_lic["owner_name"] or ""
    prev_email = latest_lic["owner_email"] or ""
    prev_wa = latest_lic["owner_whatsapp"] or ""
    
    changes = []
    if prev_name.lower() != ownerName.lower(): changes.append(f"Name: {prev_name} -> {ownerName}")
    if prev_email.lower() != ownerEmail.lower(): changes.append(f"Email: {prev_email} -> {ownerEmail}")
    if prev_wa != ownerWhatsapp: changes.append(f"WhatsApp: {prev_wa} -> {ownerWhatsapp}")
    
    change_text = "\n".join(changes) if changes else "No changes in assignment fields."
    
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute("INSERT INTO LICENSES (app_id, device_id, owner_name, owner_email, owner_whatsapp, status, renewal_requested_at) VALUES (?, ?, ?, ?, ?, 'PENDING_REVIEW', ?)",
                 (appId, deviceId, ownerName, ownerEmail, ownerWhatsapp, now_utc))
    conn.commit()
    conn.close()
    
    msg = f"⚠️ <b>Revocation Appeal Received</b>\n\n🖥️ <b>Device:</b> {deviceId}\n📝 <b>Changes:</b>\n{change_text}"
    print(f"DEBUG: Sending Telegram for appeal: {msg}")
    send_telegram(msg, get_license_buttons(deviceId, is_appeal=True))
    return {"status": "appeal_submitted"}

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {} # deviceId -> websocket
    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        self.active_connections[device_id] = websocket
    def disconnect(self, device_id: str):
        self.active_connections.pop(device_id, None)
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            try: await connection.send_json(message)
            except: pass

manager = ConnectionManager()


@app.websocket("/v1/stream")
async def websocket_endpoint(websocket: WebSocket, app: str, dev: str):
    await manager.connect(websocket, dev)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(dev)


@app.post("/admin/login")
def admin_login(data: AdminLogin):
    conn = get_db()
    user = conn.execute("SELECT * FROM ADMIN_USERS WHERE username=?", (data.username,)).fetchone()
    conn.close()
    if not user or not bcrypt.checkpw(data.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"status": "success", "token": "admin_session_token"}

@app.post("/admin/change-password")
def change_password(data: PasswordChangeRequest):
    conn = get_db()
    user = conn.execute("SELECT * FROM ADMIN_USERS WHERE username='admin'").fetchone()
    if not user or not bcrypt.checkpw(data.oldPassword.encode("utf-8"), user["password_hash"].encode("utf-8")):
        conn.close()
        raise HTTPException(status_code=401, detail="Current password incorrect")
    new_hash = bcrypt.hashpw(data.newPassword.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn.execute("UPDATE ADMIN_USERS SET password_hash=? WHERE username='admin'", (new_hash,))
    conn.commit()
    conn.close()
    return {"status": "changed"}

@app.get("/admin/licenses")
def get_licenses():
    conn = get_db()
    query = """
        SELECT l1.*, 
               (SELECT owner_name FROM LICENSES WHERE device_id = l1.device_id AND id < l1.id AND owner_name IS NOT NULL ORDER BY id DESC LIMIT 1) as prev_owner_name,
               (SELECT owner_email FROM LICENSES WHERE device_id = l1.device_id AND id < l1.id AND owner_email IS NOT NULL ORDER BY id DESC LIMIT 1) as prev_owner_email,
               (SELECT owner_whatsapp FROM LICENSES WHERE device_id = l1.device_id AND id < l1.id AND owner_whatsapp IS NOT NULL ORDER BY id DESC LIMIT 1) as prev_owner_whatsapp
        FROM LICENSES l1
        INNER JOIN (SELECT device_id, MAX(id) as max_id FROM LICENSES GROUP BY device_id) l2 ON l1.id = l2.max_id
        ORDER BY l1.id DESC
    """
    licenses = conn.execute(query).fetchall()
    conn.close()
    return [dict(l) for l in licenses]

@app.get("/admin/logs")
def get_logs(level: Optional[int] = None, show_deleted: bool = False):
    conn = get_db()
    query = "SELECT * FROM UNIFIED_LOGS WHERE is_deleted=?" if not show_deleted else "SELECT * FROM UNIFIED_LOGS WHERE is_deleted=1"
    params = [0] if not show_deleted else []
    if level and not show_deleted:
        query += " AND log_level=?"
        params.append(level)
    query += " ORDER BY created_at DESC LIMIT 1000"
    logs = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(l) for l in logs]

@app.post("/admin/assign/{license_id}")
def assign_owner(license_id: int, data: AssignRequest):
    conn = get_db()
    lic = conn.execute("SELECT id FROM LICENSES WHERE id=?", (license_id,)).fetchone()
    if not lic:
        conn.close()
        raise HTTPException(status_code=404, detail=f"License {license_id} not found")
    result = conn.execute("UPDATE LICENSES SET owner_name=?, owner_email=?, owner_whatsapp=? WHERE id=?", 
                 (data.name, data.email, data.whatsapp, license_id))
    conn.commit()
    conn.close()
    return {"status": "assigned", "rows_affected": result.rowcount}

@app.post("/admin/reactivate/{license_id}")
def reactivate_license(license_id: int, data: ReactivateRequest):
    conn = get_db()
    lic = conn.execute("SELECT * FROM LICENSES WHERE id=?", (license_id,)).fetchone()
    if lic:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        new_exp = now_utc + datetime.timedelta(days=data.days)
        conn.execute("UPDATE LICENSES SET status='ACTIVE', expires_at=? WHERE id=?", (new_exp.isoformat(), license_id))
        conn.commit()
        asyncio.create_task(manager.broadcast({"directive": "UPDATE_TOKEN", "target_device": lic["device_id"]}))
    conn.close()
    return {"status": "reactivated", "new_expires": new_exp.isoformat()}

@app.post("/admin/extend/{license_id}/{days}")
def extend_license(license_id: int, days: int):
    conn = get_db()
    lic = conn.execute("SELECT * FROM LICENSES WHERE id=?", (license_id,)).fetchone()
    if lic:
        current_exp = datetime.datetime.fromisoformat(lic["expires_at"].replace('Z', '+00:00'))
        new_exp = current_exp + datetime.timedelta(days=days)
        conn.execute("UPDATE LICENSES SET expires_at=?, status='ACTIVE' WHERE id=?", (new_exp.isoformat(), license_id))
        conn.commit()
        asyncio.create_task(manager.broadcast({"directive": "UPDATE_TOKEN", "target_device": lic["device_id"]}))
    conn.close()
    return {"status": "extended"}

@app.post("/admin/approve/{license_id}")
async def approve_license(license_id: int, background_tasks: BackgroundTasks):
    conn = get_db()
    lic = conn.execute("SELECT * FROM LICENSES WHERE id=?", (license_id,)).fetchone()
    if lic:
        grace_days = 30
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        new_exp = now_utc + datetime.timedelta(days=grace_days)
        conn.execute("UPDATE LICENSES SET status='ACTIVE', expires_at=? WHERE id=?", (new_exp.isoformat(), license_id))
        conn.commit()
        background_tasks.add_task(send_telegram, f"✅ <b>License Approved</b>\n\n🖥️ <b>Device:</b> {lic['device_id']}\n⏰ <b>New Expiry:</b> {format_server_time(new_exp)}", get_license_buttons(lic['device_id']))
        asyncio.create_task(manager.broadcast({"directive": "UPDATE_TOKEN", "target_device": lic["device_id"]}))
    conn.close()
    return {"status": "approved"}

@app.post("/admin/revoke/{license_id}")
async def revoke_license(license_id: int, background_tasks: BackgroundTasks):
    conn = get_db()
    lic = conn.execute("SELECT * FROM LICENSES WHERE id=?", (license_id,)).fetchone()
    if lic:
        conn.execute("UPDATE LICENSES SET status='REVOKED' WHERE id=?", (license_id,))
        conn.commit()
        background_tasks.add_task(send_telegram, f"🚫 <b>License Revoked</b>\n\n🖥️ <b>Device:</b> {lic['device_id']}", {
            "inline_keyboard": [[{"text": "🔄 Reactivate License", "callback_data": f"reactivate_{lic['device_id']}"}]]
        })
        asyncio.create_task(manager.broadcast({"directive": "REVOKE_IMMEDIATE", "target_device": lic["device_id"]}))
    conn.close()
    return {"status": "revoked"}

@app.post("/admin/logs/trash/{log_id}")
def trash_log(log_id: int):
    conn = get_db()
    conn.execute("UPDATE UNIFIED_LOGS SET is_deleted=1 WHERE id=?", (log_id,))
    conn.commit()
    conn.close()
    return {"status": "trashed"}

@app.post("/admin/logs/restore/{log_id}")
def restore_log(log_id: int):
    conn = get_db()
    conn.execute("UPDATE UNIFIED_LOGS SET is_deleted=0 WHERE id=?", (log_id,))
    conn.commit()
    conn.close()
    return {"status": "restored"}

@app.post("/admin/logs/empty-trash")
def empty_trash():
    conn = get_db()
    conn.execute("DELETE FROM UNIFIED_LOGS WHERE is_deleted=1")
    conn.commit()
    conn.close()
    return {"status": "emptied"}

@app.get("/admin/config")
def get_config():
    conn = get_db()
    apps = conn.execute("SELECT id, name, trial_days, reminder_days FROM APPLICATIONS").fetchall()
    conn.close()
    return [dict(a) for a in apps]

@app.post("/admin/config/{app_id}")
def update_config(app_id: str, data: AppConfig):
    conn = get_db()
    conn.execute("UPDATE APPLICATIONS SET trial_days=?, reminder_days=? WHERE id=?", (data.trialDays, data.reminderDays, app_id))
    conn.commit()
    conn.close()
    return {"status": "updated"}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_expiring_licenses())

async def check_expiring_licenses():
    while True:
        await asyncio.sleep(3600)
        conn = get_db()
        apps = conn.execute("SELECT id, name, trial_days, reminder_days FROM APPLICATIONS").fetchall()
        for app in apps:
            trial_days = app["trial_days"]
            reminder_days = app["reminder_days"]
            threshold = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=reminder_days)
            licenses = conn.execute("SELECT l.*, r.id as reminded_id FROM LICENSES l LEFT JOIN REMINDER_LOG r ON l.id=r.license_id AND DATE(r.reminded_at)=DATE('now') WHERE l.app_id=? AND l.status='ACTIVE' AND l.expires_at <= ? AND l.expires_at > datetime('now')", 
                                   (app["id"], threshold.isoformat())).fetchall()
            for lic in licenses:
                if not lic["reminded_id"]:
                    days_left = (datetime.datetime.fromisoformat(lic["expires_at"].replace('Z', '+00:00')) - datetime.datetime.now(datetime.timezone.utc)).days
                    send_telegram(f"⏰ <b>License Expiring Soon</b>\n\n📱 App: {app['id']}\n🖥️ Device: {lic['device_id']}\n👤 Owner: {lic['owner_name'] or 'Unassigned'}\n⏳ Days remaining: {days_left}\n\n<i>Reminder threshold: {reminder_days} days</i>", get_license_buttons(lic['device_id']))
                    conn.execute("INSERT INTO REMINDER_LOG (license_id, reminded_at, days_before) VALUES (?, ?, ?)", (lic["id"], datetime.datetime.now(datetime.timezone.utc).isoformat(), days_left))
                    conn.commit()
        conn.close()

@app.post("/v1/telegram-webhook")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        print(f"🔔 DEBUG WEBHOOK: Received update type: {list(update.keys())}")
        
        if "callback_query" in update:
            cb = update["callback_query"]
            data = cb.get("data", "")
            chat_id = cb["message"]["chat"]["id"]
            message_id = cb["message"]["message_id"]
            device_id = ""
            action_text = ""
            new_status = ""
            extend_days = 0
            
            print(f"🔔 DEBUG WEBHOOK: Received callback data: {data}")
            
            if data.startswith("extend_7_"):
                device_id = data.replace("extend_7_", ""); extend_days = 7; action_text = "⏱️ Extended by 7 Days"
            elif data.startswith("extend_30_"):
                device_id = data.replace("extend_30_", ""); extend_days = 30; action_text = "🗓️ Extended by 30 Days"
            elif data.startswith("extend_365_"):
                device_id = data.replace("extend_365_", ""); extend_days = 365; action_text = "📅 Extended by 1 Year"
            elif data.startswith("revoke_"):
                device_id = data.replace("revoke_", ""); new_status = "REVOKED"; action_text = "🚫 Revoked Immediately"
            elif data.startswith("reactivate_"):
                device_id = data.replace("reactivate_", ""); extend_days = 30; new_status = "ACTIVE"; action_text = "🔄 Reactivated (+30 Days)"
            elif data.startswith("approve_appeal_"):
                device_id = data.replace("approve_appeal_", ""); extend_days = 30; new_status = "ACTIVE"; action_text = "✅ Appeal Approved (+30 Days)"
            elif data.startswith("deny_appeal_"):
                device_id = data.replace("deny_appeal_", ""); new_status = "REVOKED"; action_text = "🚫 Appeal Denied (Kept Revoked)"
                
            if device_id:
                print(f"🔔 DEBUG WEBHOOK: Processing action for device {device_id}, extend_days={extend_days}, new_status={new_status}")
                conn = get_db()
                lic = conn.execute("SELECT * FROM LICENSES WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,)).fetchone()
                if lic:
                    update_fields = []
                    update_values = []
                    
                    if extend_days > 0:
                        if lic["expires_at"]:
                            current_exp = datetime.datetime.fromisoformat(lic["expires_at"].replace('Z', '+00:00'))
                        else:
                            current_exp = datetime.datetime.now(datetime.timezone.utc)
                        
                        new_exp = current_exp + datetime.timedelta(days=extend_days)
                        update_fields.append("expires_at=?")
                        update_values.append(new_exp.isoformat())
                        update_fields.append("status='ACTIVE'")
                    elif new_status:
                        update_fields.append(f"status='{new_status}'")
                    
                    if update_fields:
                        update_values.append(lic["id"])
                        query = f"UPDATE LICENSES SET {', '.join(update_fields)} WHERE id=?"
                        print(f"🔔 DEBUG WEBHOOK: Executing SQL: {query} | Values: {update_values}")
                        conn.execute(query, tuple(update_values))
                        conn.commit()
                        print(f"✅ DB Updated: {device_id} -> {new_status or 'ACTIVE'}")
                        
                        if new_status == "REVOKED":
                            asyncio.create_task(manager.broadcast({"directive": "REVOKE_IMMEDIATE", "target_device": device_id}))
                        else:
                            asyncio.create_task(manager.broadcast({"directive": "UPDATE_TOKEN", "target_device": device_id}))
                    
                    conn.close()
                    
                    safe_text = urllib.parse.quote(action_text.encode('utf-8'), safe='')
                    answer_url = f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery?callback_query_id={cb['id']}&text={safe_text}"
                    urllib.request.urlopen(answer_url)
                    print(f"✅ Telegram callback answered for {device_id}")
                    
                    # FIX: Explicitly define the string to prevent syntax errors
                    edit_msg = f"{action_text}\n\n🖥️ <b>Device:</b> {device_id}"
                    safe_edit_text = urllib.parse.quote(edit_msg.encode('utf-8'), safe='')
                    edit_url = f"https://api.telegram.org/bot{TG_TOKEN}/editMessageText?chat_id={chat_id}&message_id={message_id}&text={safe_edit_text}&parse_mode=HTML"
                    urllib.request.urlopen(edit_url)
                    print(f"✅ Telegram UI updated for {device_id}")
                else:
                    print(f"❌ DB Error: License not found for {device_id}")
                    
        return {"ok": True}
    except Exception as e:
        print(f"❌ WEBHOOK CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": True}



@app.get("/admin/devices/online-status")
def get_online_status():
    """Returns a list of currently online device IDs based on active WebSockets."""
    return {"online_devices": list(manager.active_connections.keys())}

app.mount("/", StaticFiles(directory="/frontend", html=True), name="frontend")
