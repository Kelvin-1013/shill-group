from telethon import TelegramClient
from datetime import datetime
import asyncio
import yaml
import os

class TelegramBot:
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.api_id = None
        self.api_hash = None
        self.phone = None

    async def connect(self, api_id: int, api_hash: str, phone: str):
        """Connect to Telegram"""
        try:
            self.api_id = api_id
            self.api_hash = api_hash
            self.phone = phone
            session_file = os.path.join('./sessions', phone)
            self.client = TelegramClient(session_file, api_id, api_hash)
            await self.client.connect()
            if not await self.client.is_user_authorized():
                await self.client.send_code_request(phone)
                self.is_connected = False
                return False, "Code requested"
            self.is_connected = True
            return True, "Connected successfully"
        except Exception as e:
            self.is_connected = False
            return False, str(e)

    async def sign_in(self, phone: str, code: str):
        """Sign in with code"""
        try:
            await self.client.sign_in(phone, code)
            self.is_connected = True
            return True, "Signed in successfully"
        except Exception as e:
            self.is_connected = False
            return False, str(e)

    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
