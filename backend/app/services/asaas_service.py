"""
AsaasService — Wrapper de alto nível para integração com Asaas.
Encapsula lógica de negócio sobre o AsaasClient.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.asaas import AsaasClient, AsaasError
from app.models.customer import Customer
from app.models.order import Order

logger = logging.getLogger(__name__)

_client: Optional[AsaasClient] = None


def get_asaas_client() -> AsaasClient:
    global _client
    if _client is None:
        _client = AsaasClient()
    return _client


async def ensure_asaas_customer(db: AsyncSession, customer: Customer) -> Optional[str]:
    """
    Garante que o cliente existe no Asaas. Retorna asaas_customer_id.
    Cria no Asaas se não existir, salva o ID no Customer.
    """
    if customer.asaas_customer_id:
        return customer.asaas_customer_id

    if not customer.cpf_cnpj:
        logger.warning(f"Cliente {customer.id} sem CPF/CNPJ — não pode criar no Asaas")
        return None

    try:
        client = get_asaas_client()
        asaas_cust = await client.get_or_create_customer(
            name=customer.name or "Cliente",
            cpf_cnpj=''.join(filter(str.isdigit, customer.cpf_cnpj)),
            email=customer.email,
            phone=customer.phone,
            external_reference=str(customer.id),
        )
        asaas_id = asaas_cust["id"]
        customer.asaas_customer_id = asaas_id
        await db.flush()
        logger.info(f"Asaas customer criado: {asaas_id} para cliente {customer.id}")
        return asaas_id
    except AsaasError as e:
        logger.error(f"Erro ao criar cliente Asaas para {customer.id}: {e}")
        return None


async def create_pix_for_order(
    db: AsyncSession,
    order: Order,
    customer: Customer,
) -> Optional[dict]:
    """
    Cria cobrança PIX no Asaas para o pedido.
    Salva asaas_payment_id no Order.
    Retorna dict com: asaas_payment_id, pix_key (payload copia-e-cola), qr_code_base64.
    """
    asaas_customer_id = await ensure_asaas_customer(db, customer)
    if not asaas_customer_id:
        return None

    try:
        client = get_asaas_client()
        result = await client.create_pix_payment(
            customer_id=asaas_customer_id,
            value=order.total_amount,
            description=f"Pedido #{order.order_number} - GasMaster",
            external_reference=str(order.id),
            expiration_seconds=3600,
        )
        payment_id = result["id"]
        order.asaas_payment_id = payment_id
        await db.flush()

        pix = result.get("pix", {})
        return {
            "asaas_payment_id": payment_id,
            "pix_key": pix.get("payload", ""),
            "qr_code_base64": pix.get("encodedImage", ""),
            "expiration": pix.get("expirationDate", ""),
        }
    except AsaasError as e:
        logger.error(f"Erro ao criar PIX Asaas para pedido {order.id}: {e}")
        return None


async def list_pix_payments(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None,
    customer_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """
    Consulta cobranças PIX no Asaas com filtros.
    Retorna: {"data": [...], "totalCount": int, "hasMore": bool}
    """
    client = get_asaas_client()
    params: dict = {
        "billingType": "PIX",
        "limit": limit,
        "offset": offset,
    }
    if date_from:
        params["dueDateStart"] = date_from.strftime("%Y-%m-%d")
    if date_to:
        params["dueDateFinish"] = date_to.strftime("%Y-%m-%d")
    if status:
        params["status"] = status

    try:
        result = await client._request("GET", "/payments", params=params)
        payments = result.get("data", [])

        # Filter by customer name client-side (Asaas doesn't support this filter directly)
        if customer_name:
            customer_name_lower = customer_name.lower()
            # We'd need customer details — skip for now, handled at API layer
            pass

        return {
            "data": payments,
            "totalCount": result.get("totalCount", len(payments)),
            "hasMore": result.get("hasMore", False),
        }
    except Exception as e:
        logger.error(f"Erro ao listar PIX Asaas: {e}")
        return {"data": [], "totalCount": 0, "hasMore": False}


async def create_boleto_for_order(
    db: AsyncSession,
    order: Order,
    customer: Customer,
    due_days: int = 30,
) -> Optional[dict]:
    """
    Cria boleto Asaas para pedido de cliente CNPJ após entrega.
    Retorna dict com: asaas_payment_id, boleto_url, identification_field.
    """
    asaas_customer_id = await ensure_asaas_customer(db, customer)
    if not asaas_customer_id:
        return None

    from datetime import datetime
    due_date = datetime.now() + timedelta(days=due_days)

    try:
        client = get_asaas_client()
        result = await client.create_boleto_payment(
            customer_id=asaas_customer_id,
            value=order.total_amount,
            description=f"Fornecimento gás - OS #{order.order_number}",
            due_date=due_date,
            external_reference=str(order.id),
        )
        payment_id = result["id"]

        return {
            "asaas_payment_id": payment_id,
            "boleto_url": result.get("bankSlipUrl", ""),
            "invoice_url": result.get("invoiceUrl", ""),
            "identification_field": result.get("identificationField", ""),
        }
    except AsaasError as e:
        logger.error(f"Erro ao criar boleto Asaas para pedido {order.id}: {e}")
        return None
