import httpx
from typing import Dict, Any, List, Optional
import os
import logging

logger = logging.getLogger(__name__)

class WahaService:
    def __init__(self):
        self.base_url = os.getenv("WAHA_API_URL", "http://localhost:3000")
        self.api_key = os.getenv("WAHA_API_KEY", "")
        self.session = os.getenv("WAHA_SESSION", "default")
        
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def _request(self, method: str, endpoint: str, data: dict = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/{endpoint}"
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers, params=data)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.text}")
                return {"error": str(e)}
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                return {"error": str(e)}

    async def send_text_message(self, to: str, text: str) -> Dict[str, Any]:
        """Send a text message via WAHA."""
        # Ensure 'to' ends with @c.us for simple text messages
        if "@" not in to:
            to = f"{to}@c.us"
            
        data = {
            "session": self.session,
            "chatId": to,
            "text": text
        }
        return await self._request("POST", "api/sendText", data)

    async def get_contacts(self) -> List[Dict[str, Any]]:
        """Fetch all contacts from WAHA"""
        response = await self._request("GET", f"api/contacts", {"session": self.session})
        if isinstance(response, list):
            return response
        return response.get("contacts", []) if isinstance(response, dict) else []

    async def check_number_status(self, phone: str) -> Dict[str, Any]:
        """Check if a number is registered on WhatsApp"""
        data = {
            "session": self.session,
            "phone": phone
        }
        return await self._request("POST", "api/contacts/check-exists", data)

    async def mark_as_read(self, chat_id: str) -> Dict[str, Any]:
        """Mark a chat as read."""
        data = {
            "session": self.session,
            "chatId": chat_id
        }
        return await self._request("POST", "api/sendSeen", data)

waha_service = WahaService()
