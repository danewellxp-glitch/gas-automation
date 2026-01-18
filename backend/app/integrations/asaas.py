"""
Cliente Asaas (Gateway de Pagamentos).
Suporta Pix, Cartão de Crédito e Boleto.

Documentação: https://docs.asaas.com/
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AsaasError(Exception):
    """Exceção para erros da API Asaas."""

    def __init__(self, message: str, errors: list = None, status_code: int = None):
        self.message = message
        self.errors = errors or []
        self.status_code = status_code
        super().__init__(message)


class AsaasClient:
    """
    Cliente para integração com Asaas.

    Suporta:
    - Criação de clientes
    - Cobranças Pix, Cartão e Boleto
    - Consulta de status
    - Webhooks
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = api_key or settings.asaas_api_key
        self.base_url = (base_url or settings.asaas_api_url).rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

        if not self.api_key:
            logger.warning("Asaas API key não configurada")

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP (lazy initialization)."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "access_token": self.api_key,
                },
            )
        return self._client

    async def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        params: dict = None,
    ) -> dict:
        """Faz requisição à API Asaas."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
                params=params,
            )

            result = response.json()

            if response.status_code >= 400:
                errors = result.get("errors", [])
                error_msg = errors[0].get("description") if errors else "Erro desconhecido"
                raise AsaasError(
                    message=error_msg,
                    errors=errors,
                    status_code=response.status_code,
                )

            return result

        except httpx.HTTPError as e:
            logger.error(f"Erro HTTP na API Asaas: {e}")
            raise AsaasError(f"Erro de conexão: {str(e)}")

    # ==================== Clientes ====================

    async def create_customer(
        self,
        name: str,
        cpf_cnpj: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        external_reference: Optional[str] = None,
    ) -> dict:
        """
        Cria um novo cliente no Asaas.

        Args:
            name: Nome completo
            cpf_cnpj: CPF ou CNPJ (apenas números)
            email: Email (opcional, mas recomendado)
            phone: Telefone (opcional)
            external_reference: Referência externa (nosso customer_id)
        """
        data = {
            "name": name,
            "cpfCnpj": cpf_cnpj,
        }

        if email:
            data["email"] = email
        if phone:
            data["phone"] = phone
        if external_reference:
            data["externalReference"] = external_reference

        result = await self._request("POST", "/customers", data=data)
        logger.info(f"Cliente criado no Asaas: {result.get('id')}")
        return result

    async def get_customer(self, customer_id: str) -> dict:
        """Busca cliente por ID."""
        return await self._request("GET", f"/customers/{customer_id}")

    async def find_customer_by_cpf_cnpj(self, cpf_cnpj: str) -> Optional[dict]:
        """Busca cliente por CPF/CNPJ."""
        result = await self._request(
            "GET",
            "/customers",
            params={"cpfCnpj": cpf_cnpj}
        )
        customers = result.get("data", [])
        return customers[0] if customers else None

    async def get_or_create_customer(
        self,
        name: str,
        cpf_cnpj: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        external_reference: Optional[str] = None,
    ) -> dict:
        """Busca cliente existente ou cria um novo."""
        # Tentar encontrar por CPF/CNPJ
        existing = await self.find_customer_by_cpf_cnpj(cpf_cnpj)
        if existing:
            return existing

        # Criar novo
        return await self.create_customer(
            name=name,
            cpf_cnpj=cpf_cnpj,
            email=email,
            phone=phone,
            external_reference=external_reference,
        )

    # ==================== Cobranças ====================

    async def create_payment(
        self,
        customer_id: str,
        billing_type: str,  # PIX, BOLETO, CREDIT_CARD
        value: Decimal,
        description: str,
        due_date: Optional[datetime] = None,
        external_reference: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Cria uma cobrança.

        Args:
            customer_id: ID do cliente no Asaas
            billing_type: Tipo de cobrança (PIX, BOLETO, CREDIT_CARD)
            value: Valor da cobrança
            description: Descrição
            due_date: Data de vencimento (padrão: hoje)
            external_reference: Referência externa (nosso order_id)
        """
        if due_date is None:
            due_date = datetime.now()

        data = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": float(value),
            "description": description,
            "dueDate": due_date.strftime("%Y-%m-%d"),
        }

        if external_reference:
            data["externalReference"] = external_reference

        # Adicionar campos extras específicos do tipo
        data.update(kwargs)

        result = await self._request("POST", "/payments", data=data)
        logger.info(f"Cobrança criada: {result.get('id')} - {billing_type} - R${value}")
        return result

    async def create_pix_payment(
        self,
        customer_id: str,
        value: Decimal,
        description: str,
        external_reference: Optional[str] = None,
        expiration_seconds: int = 3600,  # 1 hora
    ) -> dict:
        """
        Cria cobrança Pix.

        Retorna dados do Pix incluindo QR Code e código copia e cola.
        """
        # Criar cobrança
        payment = await self.create_payment(
            customer_id=customer_id,
            billing_type="PIX",
            value=value,
            description=description,
            external_reference=external_reference,
        )

        payment_id = payment["id"]

        # Buscar QR Code do Pix
        pix_data = await self.get_pix_qr_code(payment_id)

        return {
            **payment,
            "pix": pix_data,
        }

    async def get_pix_qr_code(self, payment_id: str) -> dict:
        """
        Obtém QR Code do Pix para uma cobrança.

        Retorna:
            {
                "encodedImage": "base64...",  # QR Code em base64
                "payload": "00020126...",      # Código copia e cola
                "expirationDate": "2024-01-01T12:00:00"
            }
        """
        result = await self._request("GET", f"/payments/{payment_id}/pixQrCode")
        return result

    async def create_boleto_payment(
        self,
        customer_id: str,
        value: Decimal,
        description: str,
        due_date: Optional[datetime] = None,
        external_reference: Optional[str] = None,
        days_after_due: int = 3,  # Dias para negativação após vencimento
    ) -> dict:
        """Cria cobrança com boleto."""
        if due_date is None:
            due_date = datetime.now() + timedelta(days=3)

        return await self.create_payment(
            customer_id=customer_id,
            billing_type="BOLETO",
            value=value,
            description=description,
            due_date=due_date,
            external_reference=external_reference,
        )

    async def create_credit_card_payment(
        self,
        customer_id: str,
        value: Decimal,
        description: str,
        credit_card: dict,
        credit_card_holder_info: dict,
        installment_count: int = 1,
        external_reference: Optional[str] = None,
    ) -> dict:
        """
        Cria cobrança com cartão de crédito.

        Args:
            credit_card: {
                "holderName": "Nome no cartão",
                "number": "4111111111111111",
                "expiryMonth": "12",
                "expiryYear": "2025",
                "ccv": "123"
            }
            credit_card_holder_info: {
                "name": "Nome completo",
                "email": "email@example.com",
                "cpfCnpj": "12345678901",
                "postalCode": "80000000",
                "addressNumber": "123",
                "phone": "41999999999"
            }
        """
        return await self.create_payment(
            customer_id=customer_id,
            billing_type="CREDIT_CARD",
            value=value,
            description=description,
            external_reference=external_reference,
            creditCard=credit_card,
            creditCardHolderInfo=credit_card_holder_info,
            installmentCount=installment_count,
        )

    # ==================== Consultas ====================

    async def get_payment(self, payment_id: str) -> dict:
        """Busca detalhes de uma cobrança."""
        return await self._request("GET", f"/payments/{payment_id}")

    async def get_payment_status(self, payment_id: str) -> str:
        """Retorna apenas o status de uma cobrança."""
        payment = await self.get_payment(payment_id)
        return payment.get("status", "UNKNOWN")

    async def list_payments(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        external_reference: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """Lista cobranças com filtros."""
        params = {"limit": limit, "offset": offset}

        if customer_id:
            params["customer"] = customer_id
        if status:
            params["status"] = status
        if external_reference:
            params["externalReference"] = external_reference

        return await self._request("GET", "/payments", params=params)

    # ==================== Ações ====================

    async def cancel_payment(self, payment_id: str) -> dict:
        """Cancela uma cobrança pendente."""
        result = await self._request("DELETE", f"/payments/{payment_id}")
        logger.info(f"Cobrança cancelada: {payment_id}")
        return result

    async def refund_payment(
        self,
        payment_id: str,
        value: Optional[Decimal] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Estorna uma cobrança paga.

        Args:
            value: Valor a estornar (None = valor total)
            description: Descrição do estorno
        """
        data = {}
        if value:
            data["value"] = float(value)
        if description:
            data["description"] = description

        result = await self._request("POST", f"/payments/{payment_id}/refund", data=data)
        logger.info(f"Estorno solicitado: {payment_id}")
        return result

    # ==================== Webhooks ====================

    async def configure_webhook(
        self,
        url: str,
        events: list[str] = None,
        enabled: bool = True,
    ) -> dict:
        """
        Configura webhook para receber notificações.

        Events disponíveis:
        - PAYMENT_CREATED
        - PAYMENT_CONFIRMED
        - PAYMENT_RECEIVED
        - PAYMENT_OVERDUE
        - PAYMENT_DELETED
        - PAYMENT_REFUNDED
        """
        if events is None:
            events = [
                "PAYMENT_CONFIRMED",
                "PAYMENT_RECEIVED",
                "PAYMENT_OVERDUE",
                "PAYMENT_REFUNDED",
            ]

        data = {
            "url": url,
            "email": "webhook@gas-automation.local",
            "enabled": enabled,
            "interrupted": False,
            "events": events,
        }

        return await self._request("POST", "/webhook", data=data)


# Instância global (singleton)
asaas_client = AsaasClient()


# Funções de conveniência
async def create_pix_payment(
    customer_name: str,
    customer_cpf_cnpj: str,
    value: Decimal,
    description: str,
    order_id: str,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
) -> dict:
    """
    Cria pagamento Pix completo (cria cliente se necessário).

    Retorna dados do pagamento incluindo QR Code.
    """
    # Criar/buscar cliente
    customer = await asaas_client.get_or_create_customer(
        name=customer_name,
        cpf_cnpj=customer_cpf_cnpj,
        email=customer_email,
        phone=customer_phone,
        external_reference=order_id,
    )

    # Criar pagamento Pix
    payment = await asaas_client.create_pix_payment(
        customer_id=customer["id"],
        value=value,
        description=description,
        external_reference=order_id,
    )

    return payment


async def check_payment_status(payment_id: str) -> dict:
    """Verifica status de um pagamento."""
    payment = await asaas_client.get_payment(payment_id)
    return {
        "id": payment["id"],
        "status": payment["status"],
        "value": payment["value"],
        "netValue": payment.get("netValue"),
        "billingType": payment["billingType"],
        "confirmedDate": payment.get("confirmedDate"),
    }
