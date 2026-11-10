import os
import asyncio
import aiohttp
from datetime import datetime

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_message(self, message: str, parse_mode: str = "HTML"):
        """Send message to Telegram"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": parse_mode
                }
                async with session.post(f"{self.api_url}/sendMessage", json=payload) as resp:
                    if resp.status != 200:
                        print(f"Telegram error: {await resp.text()}")
        except Exception as e:
            print(f"Telegram exception: {e}")
    
    async def send_license_alert(self, app_id: str, device_id: str, expires_at: str, action: str = "expiring"):
        """Send license expiration alert"""
        message = f"""
🔔 <b>CADEN License Alert</b>

 <b>Application:</b> {app_id}
🖥️ <b>Device:</b> {device_id[-8:] if len(device_id) > 8 else device_id}
⏰ <b>Expires:</b> {expires_at}
️ <b>Status:</b> {action.upper()}

<i>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
        """.strip()
        await self.send_message(message)
    
    async def send_revocation_notice(self, app_id: str, device_id: str, reason: str = "Administrative action"):
        """Send license revocation notice"""
        message = f"""
🚫 <b>License Revoked</b>

📱 <b>Application:</b> {app_id}
🖥️ <b>Device:</b> {device_id[-8:] if len(device_id) > 8 else device_id}
 <b>Reason:</b> {reason}

<i>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
        """.strip()
        await self.send_message(message)

# Global instance
telegram_bot = None

def init_telegram(bot_token: str, chat_id: str):
    global telegram_bot
    if bot_token and chat_id:
        telegram_bot = TelegramNotifier(bot_token, chat_id)
        print(f"✅ Telegram bot initialized for chat {chat_id}")
    else:
        print("️  Telegram not configured (missing BOT_TOKEN or CHAT_ID)")
