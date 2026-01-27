"""
Serviço de Pagamentos.
Integração com Asaas para Pix, Cartão de Crédito e Boleto.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.integrations.asaas import asaas_client, AsaasError
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Serviço para gerenciar pagamentos via Asaas.

    Suporta:
    - Pix (QR Code e copia-e-cola)
    - Cartão de Crédito (com parcelamento)
    - Boleto Bancário
    - Dinheiro (na entrega)
    """

    # ==================== CRIAÇÃO DE PAGAMENTOS ====================

    async def create_pix_payment(
        self,
        db: AsyncSession,
        order_id: UUID,
        customer_name: str,
        customer_cpf_cnpj: str,
        amount: Decimal,
        description: str,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
    ) -> Payment:
        """
        Cria pagamento Pix para um pedido.

        Returns:
            Payment com QR Code e código copia-e-cola
        """
        logger.info(f"Criando pagamento Pix para pedido {order_id}: R${amount}")

        try:
            # Buscar pedido
            order = await db.get(Order, order_id)
            if not order:
                raise ValueError(f"Pedido {order_id} não encontrado")

            if not order.is_payable:
                raise ValueError(f"Pedido {order_id} não pode ser pago (status: {order.status})")

            # Criar/buscar cliente no Asaas
            customer = await asaas_client.get_or_create_customer(
                name=customer_name,
                cpf_cnpj=customer_cpf_cnpj,
                email=customer_email,
                phone=customer_phone,
                external_reference=str(order_id),
            )

            # Criar cobrança Pix no Asaas
            asaas_payment = await asaas_client.create_pix_payment(
                customer_id=customer["id"],
                value=amount,
                description=description,
                external_reference=str(order_id),
            )

            # Extrair dados do Pix
            pix_data = asaas_payment.get("pix", {})

            # Criar registro de pagamento local
            payment = Payment(
                order_id=order_id,
                asaas_payment_id=asaas_payment["id"],
                asaas_customer_id=customer["id"],
                method=PaymentMethod.PIX.value,
                status=PaymentStatus.PENDING.value,
                amount=amount,
                pix_qr_code=pix_data.get("encodedImage"),
                pix_copy_paste=pix_data.get("payload"),
                pix_expiration=self._parse_datetime(pix_data.get("expirationDate")),
                due_date=self._parse_date(asaas_payment.get("dueDate")),
                gateway_response=asaas_payment,
            )

            db.add(payment)
            await db.commit()
            await db.refresh(payment)

            logger.info(f"Pagamento Pix criado: {payment.id} (Asaas: {payment.asaas_payment_id})")
            return payment

        except AsaasError as e:
            logger.error(f"Erro Asaas ao criar Pix: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro ao criar pagamento Pix: {e}")
            raise

    async def create_credit_card_payment(
        self,
        db: AsyncSession,
        order_id: UUID,
        customer_name: str,
        customer_cpf_cnpj: str,
        customer_email: str,
        customer_phone: str,
        amount: Decimal,
        description: str,
        card_holder_name: str,
        card_number: str,
        card_expiry_month: str,
        card_expiry_year: str,
        card_cvv: str,
        billing_postal_code: str,
        billing_address_number: str,
        installments: int = 1,
    ) -> Payment:
        """
        Cria pagamento com Cartão de Crédito.

        Args:
            installments: Número de parcelas (1-12)
        """
        logger.info(f"Criando pagamento Cartão para pedido {order_id}: R${amount} em {installments}x")

        try:
            # Buscar pedido
            order = await db.get(Order, order_id)
            if not order:
                raise ValueError(f"Pedido {order_id} não encontrado")

            if not order.is_payable:
                raise ValueError(f"Pedido {order_id} não pode ser pago (status: {order.status})")

            # Criar/buscar cliente no Asaas
            customer = await asaas_client.get_or_create_customer(
                name=customer_name,
                cpf_cnpj=customer_cpf_cnpj,
                email=customer_email,
                phone=customer_phone,
                external_reference=str(order_id),
            )

            # Dados do cartão
            credit_card = {
                "holderName": card_holder_name,
                "number": card_number,
                "expiryMonth": card_expiry_month,
                "expiryYear": card_expiry_year,
                "ccv": card_cvv,
            }

            # Dados do titular
            credit_card_holder_info = {
                "name": customer_name,
                "email": customer_email,
                "cpfCnpj": customer_cpf_cnpj,
                "postalCode": billing_postal_code,
                "addressNumber": billing_address_number,
                "phone": customer_phone,
            }

            # Criar cobrança no Asaas
            asaas_payment = await asaas_client.create_credit_card_payment(
                customer_id=customer["id"],
                value=amount,
                description=description,
                credit_card=credit_card,
                credit_card_holder_info=credit_card_holder_info,
                installment_count=installments,
                external_reference=str(order_id),
            )

            # Determinar status inicial
            asaas_status = asaas_payment.get("status", "PENDING")
            local_status = self._map_asaas_status(asaas_status)

            # Criar registro de pagamento local
            payment = Payment(
                order_id=order_id,
                asaas_payment_id=asaas_payment["id"],
                asaas_customer_id=customer["id"],
                method=PaymentMethod.CREDIT_CARD.value,
                status=local_status,
                amount=amount,
                card_last_digits=card_number[-4:] if len(card_number) >= 4 else None,
                due_date=self._parse_date(asaas_payment.get("dueDate")),
                gateway_response=asaas_payment,
            )

            # Se cartão foi aprovado imediatamente
            if local_status in [PaymentStatus.CONFIRMED.value, PaymentStatus.RECEIVED.value]:
                payment.paid_at = datetime.now(timezone.utc)

            db.add(payment)

            # Se pagamento foi confirmado, atualizar pedido
            if payment.is_paid:
                order.status = OrderStatus.PAID.value
                order.paid_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(payment)

            logger.info(f"Pagamento Cartão criado: {payment.id} - Status: {payment.status}")
            return payment

        except AsaasError as e:
            logger.error(f"Erro Asaas ao criar pagamento cartão: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro ao criar pagamento cartão: {e}")
            raise

    async def create_boleto_payment(
        self,
        db: AsyncSession,
        order_id: UUID,
        customer_name: str,
        customer_cpf_cnpj: str,
        amount: Decimal,
        description: str,
        due_date: Optional[datetime] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
    ) -> Payment:
        """Cria pagamento via Boleto Bancário."""
        logger.info(f"Criando pagamento Boleto para pedido {order_id}: R${amount}")

        try:
            # Buscar pedido
            order = await db.get(Order, order_id)
            if not order:
                raise ValueError(f"Pedido {order_id} não encontrado")

            if not order.is_payable:
                raise ValueError(f"Pedido {order_id} não pode ser pago (status: {order.status})")

            # Criar/buscar cliente no Asaas
            customer = await asaas_client.get_or_create_customer(
                name=customer_name,
                cpf_cnpj=customer_cpf_cnpj,
                email=customer_email,
                phone=customer_phone,
                external_reference=str(order_id),
            )

            # Criar cobrança Boleto no Asaas
            asaas_payment = await asaas_client.create_boleto_payment(
                customer_id=customer["id"],
                value=amount,
                description=description,
                due_date=due_date,
                external_reference=str(order_id),
            )

            # Criar registro de pagamento local
            payment = Payment(
                order_id=order_id,
                asaas_payment_id=asaas_payment["id"],
                asaas_customer_id=customer["id"],
                method=PaymentMethod.BOLETO.value,
                status=PaymentStatus.PENDING.value,
                amount=amount,
                boleto_url=asaas_payment.get("bankSlipUrl"),
                due_date=self._parse_date(asaas_payment.get("dueDate")),
                gateway_response=asaas_payment,
            )

            db.add(payment)
            await db.commit()
            await db.refresh(payment)

            logger.info(f"Pagamento Boleto criado: {payment.id}")
            return payment

        except AsaasError as e:
            logger.error(f"Erro Asaas ao criar boleto: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erro ao criar boleto: {e}")
            raise

    async def create_cash_payment(
        self,
        db: AsyncSession,
        order_id: UUID,
        amount: Decimal,
    ) -> Payment:
        """
        Registra pagamento em dinheiro (na entrega).
        Não vai para o Asaas.
        """
        logger.info(f"Registrando pagamento em dinheiro para pedido {order_id}")

        order = await db.get(Order, order_id)
        if not order:
            raise ValueError(f"Pedido {order_id} não encontrado")

        payment = Payment(
            order_id=order_id,
            method=PaymentMethod.CASH.value,
            status=PaymentStatus.PENDING.value,
            amount=amount,
        )

        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return payment

    # ==================== PROCESSAMENTO DE WEBHOOKS ====================

    async def handle_payment_confirmed(
        self,
        asaas_payment_id: str,
        order_id: Optional[str],
        payment_data: dict,
    ) -> None:
        """
        Processa confirmação de pagamento (webhook Asaas).

        Atualiza status do pagamento e do pedido.
        """
        logger.info(f"Processando confirmação de pagamento: {asaas_payment_id}")

        async with AsyncSessionLocal() as db:
            # Buscar pagamento por ID Asaas
            result = await db.execute(
                select(Payment).where(Payment.asaas_payment_id == asaas_payment_id)
            )
            payment = result.scalar_one_or_none()

            if not payment:
                logger.warning(f"Pagamento não encontrado: {asaas_payment_id}")
                return

            # Atualizar pagamento
            payment.status = PaymentStatus.CONFIRMED.value
            payment.paid_at = datetime.now(timezone.utc)
            payment.net_amount = Decimal(str(payment_data.get("netValue", 0)))
            payment.fee = Decimal(str(payment_data.get("fee", 0))) if payment_data.get("fee") else None

            # Buscar e atualizar pedido
            order = await db.get(Order, payment.order_id)
            if order and order.status == OrderStatus.PENDING.value:
                order.status = OrderStatus.PAID.value
                order.paid_at = datetime.now(timezone.utc)
                logger.info(f"Pedido {order.id} atualizado para PAID")

            await db.commit()

            # Notificar cliente via WhatsApp
            await self._notify_payment_confirmed(order, payment)

    async def handle_payment_overdue(
        self,
        asaas_payment_id: str,
        order_id: Optional[str],
    ) -> None:
        """Processa pagamento vencido (webhook Asaas)."""
        logger.warning(f"Pagamento vencido: {asaas_payment_id}")

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Payment).where(Payment.asaas_payment_id == asaas_payment_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = PaymentStatus.OVERDUE.value
                await db.commit()

    async def handle_payment_refunded(
        self,
        asaas_payment_id: str,
        order_id: Optional[str],
    ) -> None:
        """Processa estorno de pagamento (webhook Asaas)."""
        logger.info(f"Pagamento estornado: {asaas_payment_id}")

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Payment).where(Payment.asaas_payment_id == asaas_payment_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = PaymentStatus.REFUNDED.value
                await db.commit()

    # ==================== CONSULTAS ====================

    async def get_payment_status(
        self,
        db: AsyncSession,
        payment_id: UUID,
    ) -> Optional[Payment]:
        """Busca status de um pagamento."""
        return await db.get(Payment, payment_id)

    async def get_payment_by_asaas_id(
        self,
        db: AsyncSession,
        asaas_payment_id: str,
    ) -> Optional[Payment]:
        """Busca pagamento pelo ID do Asaas."""
        result = await db.execute(
            select(Payment).where(Payment.asaas_payment_id == asaas_payment_id)
        )
        return result.scalar_one_or_none()

    async def get_payments_by_order(
        self,
        db: AsyncSession,
        order_id: UUID,
    ) -> list[Payment]:
        """Lista todos os pagamentos de um pedido."""
        result = await db.execute(
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def sync_payment_status(
        self,
        db: AsyncSession,
        payment_id: UUID,
    ) -> Optional[Payment]:
        """
        Sincroniza status do pagamento com o Asaas.
        Útil para verificar pagamentos pendentes.
        """
        payment = await db.get(Payment, payment_id)
        if not payment or not payment.asaas_payment_id:
            return payment

        try:
            asaas_status = await asaas_client.get_payment_status(payment.asaas_payment_id)
            new_status = self._map_asaas_status(asaas_status)

            if payment.status != new_status:
                logger.info(f"Atualizando status do pagamento {payment_id}: {payment.status} -> {new_status}")
                payment.status = new_status

                if new_status in [PaymentStatus.CONFIRMED.value, PaymentStatus.RECEIVED.value]:
                    payment.paid_at = datetime.now(timezone.utc)

                await db.commit()
                await db.refresh(payment)

        except AsaasError as e:
            logger.error(f"Erro ao sincronizar status: {e.message}")

        return payment

    # ==================== AÇÕES ====================

    async def cancel_payment(
        self,
        db: AsyncSession,
        payment_id: UUID,
    ) -> bool:
        """Cancela um pagamento pendente."""
        payment = await db.get(Payment, payment_id)
        if not payment:
            return False

        if not payment.is_pending:
            logger.warning(f"Tentativa de cancelar pagamento não pendente: {payment_id}")
            return False

        try:
            if payment.asaas_payment_id:
                await asaas_client.cancel_payment(payment.asaas_payment_id)

            payment.status = PaymentStatus.FAILED.value
            await db.commit()

            logger.info(f"Pagamento cancelado: {payment_id}")
            return True

        except AsaasError as e:
            logger.error(f"Erro ao cancelar pagamento: {e.message}")
            return False

    async def refund_payment(
        self,
        db: AsyncSession,
        payment_id: UUID,
        value: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Estorna um pagamento."""
        payment = await db.get(Payment, payment_id)
        if not payment:
            return False

        if not payment.is_paid:
            logger.warning(f"Tentativa de estornar pagamento não pago: {payment_id}")
            return False

        try:
            if payment.asaas_payment_id:
                await asaas_client.refund_payment(
                    payment.asaas_payment_id,
                    value=value,
                    description=reason,
                )

            payment.status = PaymentStatus.REFUND_REQUESTED.value
            await db.commit()

            logger.info(f"Estorno solicitado: {payment_id}")
            return True

        except AsaasError as e:
            logger.error(f"Erro ao estornar pagamento: {e.message}")
            return False

    # ==================== MÉTODOS AUXILIARES ====================

    def _map_asaas_status(self, asaas_status: str) -> str:
        """Mapeia status do Asaas para status local."""
        mapping = {
            "PENDING": PaymentStatus.PENDING.value,
            "RECEIVED": PaymentStatus.RECEIVED.value,
            "CONFIRMED": PaymentStatus.CONFIRMED.value,
            "OVERDUE": PaymentStatus.OVERDUE.value,
            "REFUNDED": PaymentStatus.REFUNDED.value,
            "REFUND_REQUESTED": PaymentStatus.REFUND_REQUESTED.value,
            "REFUND_IN_PROGRESS": PaymentStatus.REFUND_REQUESTED.value,
            "CHARGEBACK_REQUESTED": PaymentStatus.CHARGEBACK_REQUESTED.value,
            "CHARGEBACK_DISPUTE": PaymentStatus.CHARGEBACK_DISPUTE.value,
            "AWAITING_CHARGEBACK_REVERSAL": PaymentStatus.AWAITING_CHARGEBACK_REVERSAL.value,
            "DUNNING_REQUESTED": PaymentStatus.DUNNING_REQUESTED.value,
            "DUNNING_RECEIVED": PaymentStatus.DUNNING_RECEIVED.value,
            "AWAITING_RISK_ANALYSIS": PaymentStatus.AWAITING_RISK_ANALYSIS.value,
        }
        return mapping.get(asaas_status, PaymentStatus.PENDING.value)

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse datetime string do Asaas."""
        if not value:
            return None
        try:
            # Asaas retorna formato ISO
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        """Parse date string do Asaas (YYYY-MM-DD)."""
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            return None

    async def _notify_payment_confirmed(
        self,
        order: Optional[Order],
        payment: Payment,
    ) -> None:
        """Envia notificação de pagamento confirmado via WhatsApp."""
        if not order:
            return

        try:
            from app.integrations.waha import waha_client
            from app.models.customer import Customer

            # Buscar cliente
            async with AsyncSessionLocal() as db:
                customer = await db.get(Customer, order.customer_id)
                if not customer:
                    return

                message = (
                    f"*Pagamento Confirmado!* \n\n"
                    f"Seu pagamento de R$ {payment.amount:.2f} foi confirmado.\n"
                    f"Pedido #{order.order_number}\n\n"
                    f"Estamos preparando sua entrega!"
                )

                await waha_client.send_text(customer.phone, message)
                logger.info(f"Notificação de pagamento enviada para {customer.phone}")

        except Exception as e:
            logger.error(f"Erro ao enviar notificação de pagamento: {e}")


# Instância global
payment_service = PaymentService()
