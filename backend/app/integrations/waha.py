"""
Cliente WAHA (WhatsApp HTTP API).
Gerencia envio e recebimento de mensagens via WhatsApp.
"""

import asyncio
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
        # Cache de LID -> número real (@c.us) para evitar chamadas repetidas
        self._lid_cache: Dict[str, str] = {}

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

        WAHA não aceita @lid em chatId ao enviar; usar sempre @c.us.
        Input: 5541999999999, 41999999999, 7185547411514@lid ou 5541999999999@c.us
        Output: 5541999999999@c.us
        """
        # Se já é @c.us, retorna como está
        if phone and "@c.us" in phone:
            return phone

        # Remove sufixo @lid ou @c.us e extrai só os dígitos (WAHA exige @c.us para envio)
        cleaned = "".join(filter(str.isdigit, (phone or "").split("@")[0]))
        if not cleaned:
            return phone  # fallback

        # Adiciona código do país se necessário
        if len(cleaned) == 11:
            cleaned = f"55{cleaned}"
        elif len(cleaned) == 10:
            cleaned = f"55{cleaned}"

        return f"{cleaned}@c.us"

    async def resolve_lid(self, lid: str) -> str:
        """
        Resolve um LID (Linked ID) para o número real do telefone.

        Usa o endpoint GET /api/contacts?contactId={lid} do WAHA que retorna
        o campo 'number' com o telefone real do contato.

        Args:
            lid: ID no formato "7185547411514@lid" ou "7185547411514"

        Returns:
            Número no formato "5541999999999@c.us" ou o próprio lid se falhar
        """
        # Se não é @lid, formata normalmente
        if not lid or "@lid" not in lid:
            return self._format_phone(lid)

        # 1. Verificar cache em memória (mesmo worker)
        if lid in self._lid_cache:
            logger.debug(f"LID cache hit (mem): {lid} -> {self._lid_cache[lid]}")
            return self._lid_cache[lid]

        # 2. Verificar cache Redis (cross-worker)
        try:
            from app.database import redis_manager
            redis = redis_manager.client
            cached = await redis.get(f"lid_resolve:{lid}")
            if cached:
                self._lid_cache[lid] = cached
                logger.debug(f"LID cache hit (redis): {lid} -> {cached}")
                return cached
        except Exception:
            pass

        client = await self._get_client()

        # 3. MÉTODO PRINCIPAL: GET /api/contacts?contactId={lid}&session={session}
        #    Conforme GUIA-RESOLUCAO-LID-WAHA.md - retorna objeto com campo 'number' = telefone real
        try:
            response = await client.get(
                "/api/contacts",
                params={"contactId": lid, "session": self.session_name}
            )
            if response.status_code == 200:
                data = response.json()
                # WAHA pode retornar objeto único ou lista
                contact = data[0] if isinstance(data, list) and data else data
                if isinstance(contact, dict):
                    # Campo 'number' é o telefone real (ex: "5541999999999") - conforme guia
                    real_number = contact.get("number")
                    if real_number:
                        # Formatar como @c.us para consistência
                        resolved = f"{real_number}@c.us"
                        await self._cache_lid(lid, resolved)
                        logger.info(f"LID resolvido via /api/contacts.number: {lid} -> {resolved}")
                        return resolved
                    # Fallback: campo 'id' se contém @c.us (algumas versões do WAHA)
                    cid = contact.get("id", "")
                    if cid and "@c.us" in str(cid):
                        await self._cache_lid(lid, cid)
                        logger.info(f"LID resolvido via /api/contacts.id: {lid} -> {cid}")
                        return cid
        except Exception as e:
            logger.debug(f"LID /api/contacts falhou: {e}")

        # 4. Fallback: buscar no banco Customer com waha_chat_id == lid
        try:
            from app.database import AsyncSessionLocal
            from app.models.customer import Customer
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Customer).where(Customer.waha_chat_id == lid)
                )
                customer = result.scalar_one_or_none()
                if customer and customer.phone:
                    resolved = self._format_phone(customer.phone)
                    await self._cache_lid(lid, resolved)
                    logger.info(f"LID resolvido via DB: {lid} -> {resolved}")
                    return resolved
        except Exception as e:
            logger.debug(f"LID DB lookup falhou: {e}")

        logger.warning(f"Não foi possível resolver LID {lid} - mantendo original")
        return lid

    async def _cache_lid(self, lid: str, resolved: str) -> None:
        """Armazena resolução LID em memória e Redis (TTL 24h)."""
        self._lid_cache[lid] = resolved
        try:
            from app.database import redis_manager
            await redis_manager.client.set(
                f"lid_resolve:{lid}", resolved, ex=86400
            )
        except Exception:
            pass

    async def get_contact_info(self, contact_id: str) -> Optional[Dict]:
        """
        Busca informações completas de um contato no WAHA.

        Retorna dict com: number, pushname, name, isBusiness
        ou None se falhar.
        """
        try:
            client = await self._get_client()
            response = await client.get(
                "/api/contacts",
                params={"contactId": contact_id, "session": self.session_name}
            )
            if response.status_code == 200:
                data = response.json()
                contact = data[0] if isinstance(data, list) and data else data
                if isinstance(contact, dict):
                    return {
                        "number": contact.get("number"),
                        "pushname": contact.get("pushname"),
                        "name": contact.get("name") or contact.get("shortName"),
                        "isBusiness": contact.get("isBusiness", False),
                    }
        except Exception as e:
            logger.debug(f"get_contact_info falhou para {contact_id}: {e}")
        return None

    async def _get_chat_id(self, phone: str) -> str:
        """
        Obtém o chat_id correto para envio, resolvendo LID se necessário.
        """
        if "@lid" in phone:
            return await self.resolve_lid(phone)
        return self._format_phone(phone)

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

    async def ensure_session_ready(self) -> bool:
        """
        Garante que a sessão WAHA está WORKING.
        Se estiver STOPPED, inicia a sessão. Idempotente e best-effort:
        não levanta exceção para não travar o startup do backend.
        Retorna True se a sessão está (ou ficou) WORKING, False caso contrário.
        """
        try:
            data = await self.get_session_status()
            status = (data.get("status") or "").upper()
            if status == "WORKING":
                logger.info("WAHA sessão já WORKING")
                return True
            if status == "STOPPED":
                logger.warning("WAHA sessão STOPPED; iniciando sessão no startup...")
                await self.start_session()
                await asyncio.sleep(2)
                data = await self.get_session_status()
                new_status = (data.get("status") or "").upper()
                if new_status == "WORKING":
                    logger.info("WAHA sessão iniciada com sucesso (WORKING)")
                    return True
                logger.warning(f"WAHA sessão após start: {new_status} (aguardar WORKING)")
                return False
            logger.info(f"WAHA sessão em estado {status} (aguardar WORKING se necessário)")
            return status == "WORKING"
        except Exception as e:
            logger.warning("WAHA ensure_session_ready falhou (best-effort): %s", e)
            return False

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
            phone: Número do destinatário (pode ser @lid ou @c.us)
            text: Texto da mensagem
        """
        client = await self._get_client()

        # Resolver LID para número real se necessário
        if "@lid" in phone:
            chat_id = await self.resolve_lid(phone)
        else:
            chat_id = await self._get_chat_id(phone)

        payload = {
            "chatId": chat_id,
            "text": text,
            "session": self.session_name,
        }

        try:
            response = await client.post("/api/sendText", json=payload)
            if response.status_code == 422:
                body = response.json() if response.content else {}
                err = body.get("response", body)
                status = err.get("status") if isinstance(err, dict) else None
                error_msg = body.get("message", "")
                logger.warning(
                    f"WAHA sendText 422: status={status} msg={error_msg} body={body!r}"
                )
                # Sessão não está WORKING - tentar reiniciar
                if status and status != "WORKING":
                    logger.warning(
                        f"WAHA sessão {status}. Iniciando sessão e reenviando..."
                    )
                    try:
                        await client.post(
                            f"/api/sessions/{self.session_name}/start",
                            json={},
                        )
                    except Exception as start_err:
                        logger.debug(f"Start session: {start_err}")
                    await asyncio.sleep(3)
                    retry = await client.post("/api/sendText", json=payload)
                    if retry.is_success:
                        result = retry.json()
                        logger.info(f"Mensagem enviada para {phone} (após start+retry)")
                        return result
                    retry_body = retry.json() if retry.content else {}
                    logger.error(f"Retry também falhou: {retry.status_code} {retry_body}")
                    raise httpx.HTTPStatusError(
                        f"WAHA sendText falhou após retry: {retry_body}",
                        request=retry.request,
                        response=retry,
                    )
                # 422 sem status de sessão - erro de validação (chatId inválido, etc)
                raise httpx.HTTPStatusError(
                    f"WAHA rejeitou mensagem: {error_msg or body}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Mensagem enviada para {phone}: {text[:50]}...")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar mensagem para {phone} (chatId={chat_id}): {e}")
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
        chat_id = await self._get_chat_id(phone)

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
        chat_id = await self._get_chat_id(phone)

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
        chat_id = await self._get_chat_id(phone)

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
        chat_id = await self._get_chat_id(phone)

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

    async def send_typing(self, phone: str, typing: bool = True) -> dict:
        """
        Envia indicador de "digitando..." para o cliente.

        Args:
            phone: Número do destinatário
            typing: True para iniciar, False para parar

        Isso melhora a UX mostrando que o bot está processando.
        """
        client = await self._get_client()
        chat_id = self._format_phone(phone)

        payload = {
            "chatId": chat_id,
            "session": self.session_name,
        }

        try:
            if typing:
                # Iniciar "digitando..."
                response = await client.post("/api/startTyping", json=payload)
            else:
                # Parar "digitando..."
                response = await client.post("/api/stopTyping", json=payload)

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            # Não é crítico se falhar
            logger.debug(f"Erro ao enviar typing para {phone}: {e}")
            return {}

    async def mark_as_read(self, phone: str, message_id: str) -> dict:
        """Marca mensagem como lida (✓✓ azul)."""
        client = await self._get_client()
        chat_id = await self._get_chat_id(phone)

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
            if getattr(e, "response", None) and getattr(e.response, "status_code", None) == 404:
                logger.debug("WAHA markAsRead não disponível (404); ignorando.")
            else:
                logger.warning(f"Erro ao marcar como lido: {e}")
            return {}

    async def start_typing(self, phone: str) -> None:
        """Inicia indicador de 'digitando...' para o cliente."""
        try:
            client = await self._get_client()
            chat_id = await self._get_chat_id(phone)
            payload = {
                "chatId": chat_id,
                "session": self.session_name,
            }
            response = await client.post("/api/startTyping", json=payload)
            if response.status_code not in (200, 201):
                logger.debug(f"startTyping retornou {response.status_code}")
        except Exception as e:
            logger.debug(f"Erro ao iniciar typing para {phone}: {e}")

    async def stop_typing(self, phone: str) -> None:
        """Para indicador de 'digitando...' para o cliente."""
        try:
            client = await self._get_client()
            chat_id = await self._get_chat_id(phone)
            payload = {
                "chatId": chat_id,
                "session": self.session_name,
            }
            response = await client.post("/api/stopTyping", json=payload)
            if response.status_code not in (200, 201):
                logger.debug(f"stopTyping retornou {response.status_code}")
        except Exception as e:
            logger.debug(f"Erro ao parar typing para {phone}: {e}")

    async def check_number_exists(self, phone: str) -> bool:
        """Verifica se o número existe no WhatsApp."""
        client = await self._get_client()
        chat_id = await self._get_chat_id(phone)

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
