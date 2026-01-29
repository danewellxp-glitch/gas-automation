"""
Cliente WAHA (WhatsApp HTTP API).
Gerencia envio e recebimento de mensagens via WhatsApp.
"""

import base64
import logging
from typing import Optional, List, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WAHAClient:
    """
    Cliente para integração com WAHA (WhatsApp HTTP API).

    Documentação: https://waha.devlike.pro/docs/
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        session_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or settings.waha_url).rstrip("/")
        self.session_name = session_name or settings.waha_session_name
        self.api_key = api_key or settings.waha_api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP (lazy initialization)."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-Api-Key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _format_phone(self, phone: str) -> str:
        """
        Formata número de telefone para o formato WAHA.

        Se já tiver sufixo @lid ou @c.us, mantém como está.
        Input: 5541999999999 ou 41999999999 ou 7185547411514@lid
        Output: 5541999999999@c.us ou 7185547411514@lid
        """
        # Se já tem sufixo, manter como está
        if "@" in phone:
            return phone

        # Remove caracteres não numéricos
        cleaned = "".join(filter(str.isdigit, phone))

        # Adiciona código do país se necessário
        if len(cleaned) == 11:
            cleaned = f"55{cleaned}"
        elif len(cleaned) == 10:
            cleaned = f"55{cleaned}"

        return f"{cleaned}@c.us"

    # ==================== Sessão ====================

    async def get_session_status(self) -> dict:
        """Verifica status da sessão WhatsApp."""
        client = await self._get_client()
        try:
            response = await client.get(f"/api/sessions/{self.session_name}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Erro ao verificar sessão: {e}")
            return {"status": "error", "error": str(e)}

    async def start_session(self) -> dict:
        """Inicia uma nova sessão WhatsApp."""
        client = await self._get_client()
        try:
            response = await client.post(
                f"/api/sessions/{self.session_name}/start"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Erro ao iniciar sessão: {e}")
            raise

    async def get_qr_code(self) -> Optional[str]:
        """Obtém QR Code para autenticação (base64)."""
        client = await self._get_client()
        try:
            response = await client.get(
                f"/api/sessions/{self.session_name}/auth/qr",
                params={"format": "base64"}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("qr") or data.get("data")
            return None
        except httpx.HTTPError as e:
            logger.error(f"Erro ao obter QR Code: {e}")
            return None

    # ==================== Envio de Mensagens ====================

    async def send_text(self, phone: str, text: str) -> dict:
        """
        Envia mensagem de texto simples.

        Args:
            phone: Número do destinatário
            text: Texto da mensagem
        """
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        payload = {
            "chatId": chat_id,
            "text": text,
            "session": self.session_name,
        }

        try:
            response = await client.post("/api/sendText", json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Mensagem enviada para {phone}: {text[:50]}...")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar mensagem para {phone}: {e}")
            raise

    async def send_buttons(
        self,
        phone: str,
        text: str,
        buttons: List[Dict],
        footer: Optional[str] = None,
    ) -> Dict:
        """
        Envia mensagem com botões interativos.

        Args:
            phone: Número do destinatário
            text: Texto principal da mensagem
            buttons: Lista de botões [{"id": "btn1", "text": "Opção 1"}, ...]
            footer: Texto de rodapé (opcional)

        Nota: WhatsApp permite máximo de 3 botões.
        """
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        # Formatar botões para o formato WAHA
        formatted_buttons = [
            {"id": btn["id"], "text": btn["text"][:20]}  # Max 20 chars
            for btn in buttons[:3]  # Max 3 botões
        ]

        payload = {
            "chatId": chat_id,
            "text": text,
            "buttons": formatted_buttons,
            "session": self.session_name,
        }

        if footer:
            payload["footer"] = footer

        try:
            response = await client.post("/api/sendButtons", json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Botões enviados para {phone}")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar botões para {phone}: {e}")
            # Fallback: enviar como texto com opções numeradas
            return await self._send_buttons_as_text(phone, text, buttons, footer)

    async def _send_buttons_as_text(
        self,
        phone: str,
        text: str,
        buttons: List[Dict],
        footer: Optional[str] = None,
    ) -> Dict:
        """Fallback: envia botões como texto com opções numeradas."""
        options_text = "\n".join(
            f"{i+1}. {btn['text']}" for i, btn in enumerate(buttons)
        )
        full_text = f"{text}\n\n{options_text}"
        if footer:
            full_text += f"\n\n{footer}"

        return await self.send_text(phone, full_text)

    async def send_list(
        self,
        phone: str,
        text: str,
        button_text: str,
        sections: List[Dict],
    ) -> Dict:
        """
        Envia mensagem com lista de seleção.

        Args:
            phone: Número do destinatário
            text: Texto principal
            button_text: Texto do botão que abre a lista
            sections: Seções da lista [{"title": "Seção", "rows": [{"id": "1", "title": "Item"}]}]
        """
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        payload = {
            "chatId": chat_id,
            "text": text,
            "buttonText": button_text,
            "sections": sections,
            "session": self.session_name,
        }

        try:
            response = await client.post("/api/sendList", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar lista para {phone}: {e}")
            raise

    async def send_image(
        self,
        phone: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> Dict:
        """
        Envia imagem.

        Args:
            phone: Número do destinatário
            image_url: URL da imagem (alternativa a base64)
            image_base64: Imagem em base64 (alternativa a URL)
            caption: Legenda da imagem
        """
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        payload = {
            "chatId": chat_id,
            "session": self.session_name,
        }

        if image_url:
            payload["file"] = {"url": image_url}
        elif image_base64:
            payload["file"] = {"data": image_base64}
        else:
            raise ValueError("Forneça image_url ou image_base64")

        if caption:
            payload["caption"] = caption

        try:
            response = await client.post("/api/sendImage", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar imagem para {phone}: {e}")
            raise

    async def send_document(
        self,
        phone: str,
        document_url: str,
        filename: str,
        caption: Optional[str] = None,
    ) -> Dict:
        """Envia documento (PDF, etc)."""
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        payload = {
            "chatId": chat_id,
            "file": {"url": document_url},
            "filename": filename,
            "session": self.session_name,
        }

        if caption:
            payload["caption"] = caption

        try:
            response = await client.post("/api/sendFile", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar documento para {phone}: {e}")
            raise

    # ==================== Utilitários ====================

    async def mark_as_read(self, phone: str, message_id: str) -> dict:
        """Marca mensagem como lida."""
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        payload = {
            "chatId": chat_id,
            "messageId": message_id,
            "session": self.session_name,
        }

        try:
            response = await client.post("/api/markAsRead", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.warning(f"Erro ao marcar como lido: {e}")
            return {}

    async def check_number_exists(self, phone: str) -> bool:
        """Verifica se o número existe no WhatsApp."""
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        try:
            response = await client.get(
                f"/api/contacts/check-exists",
                params={"chatId": chat_id, "session": self.session_name}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("exists", False)
            return False
        except httpx.HTTPError:
            return False


# Instância global (singleton)
waha_client = WAHAClient()


# Funções de conveniência para uso direto
async def send_message(phone: str, text: str) -> dict:
    """Envia mensagem de texto."""
    return await waha_client.send_text(phone, text)


async def send_buttons(
    phone: str,
    text: str,
    buttons: List[Dict],
    footer: Optional[str] = None,
) -> dict:
    """Envia mensagem com botões."""
    return await waha_client.send_buttons(phone, text, buttons, footer)


async def send_image(
    phone: str,
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    caption: Optional[str] = None,
) -> dict:
    """Envia imagem."""
    return await waha_client.send_image(phone, image_url, image_base64, caption)
