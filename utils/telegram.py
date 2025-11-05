
import aiohttp
from typing import Optional

class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 20):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base = f"https://api.telegram.org/bot{self.bot_token}"
        self.timeout = timeout

    async def _post(self, method: str, payload: dict):
        url = f"{self.base}/{method}"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(url, json=payload) as r:
                if r.status != 200:
                    text = await r.text()
                    raise RuntimeError(f"Telegram HTTP {r.status}: {text}")
                return await r.json()

    async def send(self, text: str):
        return await self._post("sendMessage", {"chat_id": self.chat_id, "text": text})

    async def log(self, text: str):
        # same as send, separated so we could extend later (e.g., different chat or disable)
        return await self.send(text)
