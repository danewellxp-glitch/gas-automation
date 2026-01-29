"""
Daily Business Summary Service.

Gera e envia resumo diário de negócios para o owner via WhatsApp/Email.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from decimal import Decimal

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.customer import Customer
from app.services.event_publisher import event_publisher

logger = logging.getLogger(__name__)


class DailySummaryService:
    """Serviço para gerar resumo diário de negócios."""
    
    def __init__(self):
        self.template_cache: Optional[Dict[str, Any]] = None
    
    async def generate_summary(self, db: AsyncSession, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Gera resumo diário de negócios.
        
        Args:
            db: Sessão do banco de dados
            date: Data do resumo (default: hoje)
            
        Returns:
            Dicionário com métricas do dia
        """
        if not date:
            date = datetime.now(timezone.utc)
        
        # Início e fim do dia
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # Total de pedidos
        total_orders_result = await db.execute(
            select(func.count(Order.id))
            .where(Order.created_at >= day_start)
            .where(Order.created_at < day_end)
        )
        total_orders = total_orders_result.scalar() or 0
        
        # Pedidos por status
        orders_by_status_result = await db.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.created_at >= day_start)
            .where(Order.created_at < day_end)
            .group_by(Order.status)
        )
        orders_by_status = {row[0]: row[1] for row in orders_by_status_result.fetchall()}
        
        # Faturamento (pedidos entregues)
        revenue_result = await db.execute(
            select(func.sum(Order.total_amount))
            .where(Order.created_at >= day_start)
            .where(Order.created_at < day_end)
            .where(Order.status == OrderStatus.DELIVERED.value)
        )
        revenue = float(revenue_result.scalar() or 0)
        
        # Pagamentos confirmados
        payments_result = await db.execute(
            select(func.sum(Payment.amount))
            .where(Payment.created_at >= day_start)
            .where(Payment.created_at < day_end)
            .where(Payment.status == PaymentStatus.CONFIRMED.value)
        )
        payments_received = float(payments_result.scalar() or 0)
        
        # Novos clientes
        new_customers_result = await db.execute(
            select(func.count(Customer.id))
            .where(Customer.created_at >= day_start)
            .where(Customer.created_at < day_end)
        )
        new_customers = new_customers_result.scalar() or 0
        
        # Pedidos pendentes (não entregues)
        pending_orders = orders_by_status.get(OrderStatus.PENDING.value, 0)
        paid_orders = orders_by_status.get(OrderStatus.PAID.value, 0)
        preparing_orders = orders_by_status.get(OrderStatus.PREPARING.value, 0)
        dispatched_orders = orders_by_status.get(OrderStatus.DISPATCHED.value, 0)
        total_pending = pending_orders + paid_orders + preparing_orders + dispatched_orders
        
        # Taxa de conversão (entregues / total)
        conversion_rate = (orders_by_status.get(OrderStatus.DELIVERED.value, 0) / total_orders * 100) if total_orders > 0 else 0
        
        # Ticket médio
        avg_ticket = revenue / orders_by_status.get(OrderStatus.DELIVERED.value, 1) if orders_by_status.get(OrderStatus.DELIVERED.value, 0) > 0 else 0
        
        summary = {
            "date": day_start.date().isoformat(),
            "total_orders": total_orders,
            "orders_by_status": orders_by_status,
            "delivered_orders": orders_by_status.get(OrderStatus.DELIVERED.value, 0),
            "cancelled_orders": orders_by_status.get(OrderStatus.CANCELLED.value, 0),
            "pending_orders": total_pending,
            "revenue": revenue,
            "payments_received": payments_received,
            "new_customers": new_customers,
            "conversion_rate": round(conversion_rate, 2),
            "avg_ticket": round(avg_ticket, 2),
        }
        
        return summary
    
    def format_summary_text(self, summary: Dict[str, Any]) -> str:
        """
        Formata resumo como texto para WhatsApp/SMS.
        
        Args:
            summary: Dicionário com métricas
            
        Returns:
            Texto formatado
        """
        date_str = datetime.fromisoformat(summary["date"]).strftime("%d/%m/%Y")
        
        text = f"""📊 *Resumo Diário - {date_str}*

📦 *Pedidos*
• Total: {summary['total_orders']}
• Entregues: {summary['delivered_orders']}
• Pendentes: {summary['pending_orders']}
• Cancelados: {summary['cancelled_orders']}

💰 *Financeiro*
• Faturamento: R$ {summary['revenue']:,.2f}
• Pagamentos recebidos: R$ {summary['payments_received']:,.2f}
• Ticket médio: R$ {summary['avg_ticket']:,.2f}

👥 *Clientes*
• Novos clientes: {summary['new_customers']}

📈 *Métricas*
• Taxa de conversão: {summary['conversion_rate']:.1f}%

"""
        
        # Adicionar alertas se necessário
        if summary['pending_orders'] > 10:
            text += f"⚠️ *Alerta:* {summary['pending_orders']} pedidos pendentes!\n"
        
        if summary['conversion_rate'] < 70:
            text += f"⚠️ *Alerta:* Taxa de conversão abaixo do esperado ({summary['conversion_rate']:.1f}%)\n"
        
        return text
    
    def format_summary_html(self, summary: Dict[str, Any]) -> str:
        """
        Formata resumo como HTML para Email.
        
        Args:
            summary: Dicionário com métricas
            
        Returns:
            HTML formatado
        """
        date_str = datetime.fromisoformat(summary["date"]).strftime("%d/%m/%Y")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #333; }}
                .metric {{ margin: 10px 0; }}
                .label {{ font-weight: bold; }}
                .alert {{ color: #d32f2f; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Resumo Diário - {date_str}</h1>
            
            <h2>Pedidos</h2>
            <div class="metric">
                <span class="label">Total:</span> {summary['total_orders']}
            </div>
            <div class="metric">
                <span class="label">Entregues:</span> {summary['delivered_orders']}
            </div>
            <div class="metric">
                <span class="label">Pendentes:</span> {summary['pending_orders']}
            </div>
            <div class="metric">
                <span class="label">Cancelados:</span> {summary['cancelled_orders']}
            </div>
            
            <h2>Financeiro</h2>
            <div class="metric">
                <span class="label">Faturamento:</span> R$ {summary['revenue']:,.2f}
            </div>
            <div class="metric">
                <span class="label">Pagamentos recebidos:</span> R$ {summary['payments_received']:,.2f}
            </div>
            <div class="metric">
                <span class="label">Ticket médio:</span> R$ {summary['avg_ticket']:,.2f}
            </div>
            
            <h2>Clientes</h2>
            <div class="metric">
                <span class="label">Novos clientes:</span> {summary['new_customers']}
            </div>
            
            <h2>Métricas</h2>
            <div class="metric">
                <span class="label">Taxa de conversão:</span> {summary['conversion_rate']:.1f}%
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def send_summary(
        self,
        db: AsyncSession,
        owner_phone: Optional[str] = None,
        owner_email: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> bool:
        """
        Gera e envia resumo diário.
        
        Args:
            db: Sessão do banco de dados
            owner_phone: Telefone do owner (para WhatsApp)
            owner_email: Email do owner
            date: Data do resumo (default: hoje)
            
        Returns:
            True se enviado com sucesso
        """
        try:
            # Gerar resumo
            summary = await self.generate_summary(db, date)
            
            # Formatar mensagens
            text_message = self.format_summary_text(summary)
            html_message = self.format_summary_html(summary)
            
            # Enviar via WhatsApp se disponível
            if owner_phone:
                await event_publisher.publish_notification(
                    notification_type="whatsapp",
                    recipient_phone=owner_phone,
                    message=text_message,
                )
            
            # Enviar via Email se disponível
            if owner_email:
                await event_publisher.publish_notification(
                    notification_type="email",
                    recipient_email=owner_email,
                    subject=f"Resumo Diário - {summary['date']}",
                    message=html_message,
                    template="daily_summary",
                    template_data=summary,
                )
            
            logger.info(f"Resumo diário enviado para {date or datetime.now(timezone.utc).date()}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar resumo diário: {e}", exc_info=True)
            return False


# Instância global
daily_summary_service = DailySummaryService()