"""
Cliente SendGrid para envio de emails.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# SendGrid SDK é opcional
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid SDK não instalado")


def get_sendgrid_client() -> Optional["SendGridAPIClient"]:
    """Retorna cliente SendGrid se disponível e configurado."""
    if not SENDGRID_AVAILABLE:
        return None

    if not settings.sendgrid_enabled:
        logger.warning("SendGrid não configurado")
        return None

    return SendGridAPIClient(settings.sendgrid_api_key)


async def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    to_name: Optional[str] = None,
) -> bool:
    """
    Envia email via SendGrid.

    Args:
        to_email: Email do destinatário
        subject: Assunto do email
        body_text: Corpo em texto plano
        body_html: Corpo em HTML (opcional)
        to_name: Nome do destinatário (opcional)

    Returns:
        True se enviado com sucesso
    """
    client = get_sendgrid_client()
    if not client:
        logger.warning(f"Email não enviado (SendGrid desabilitado): {to_email}")
        return False

    try:
        # Construir email
        from_email = Email(settings.sendgrid_from_email, settings.sendgrid_from_name)
        to = To(to_email, to_name)

        # Conteúdo
        content_plain = Content("text/plain", body_text)
        content_html = Content("text/html", body_html) if body_html else None

        # Criar mensagem
        message = Mail(
            from_email=from_email,
            to_emails=to,
            subject=subject,
        )
        message.content = [content_plain]
        if content_html:
            message.content.append(content_html)

        # Enviar
        response = client.send(message)

        if response.status_code in [200, 201, 202]:
            logger.info(f"Email enviado: {to_email} - {subject}")
            return True
        else:
            logger.error(f"Erro ao enviar email: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Erro SendGrid ao enviar email: {e}")
        return False


async def send_template_email(
    to_email: str,
    template_id: str,
    template_data: dict,
    to_name: Optional[str] = None,
) -> bool:
    """
    Envia email usando template do SendGrid.

    Args:
        to_email: Email do destinatário
        template_id: ID do template no SendGrid
        template_data: Dados para substituição no template
        to_name: Nome do destinatário

    Returns:
        True se enviado com sucesso
    """
    client = get_sendgrid_client()
    if not client:
        return False

    try:
        message = Mail(
            from_email=Email(settings.sendgrid_from_email, settings.sendgrid_from_name),
            to_emails=To(to_email, to_name),
        )
        message.template_id = template_id
        message.dynamic_template_data = template_data

        response = client.send(message)

        if response.status_code in [200, 201, 202]:
            logger.info(f"Email template enviado: {to_email}")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao enviar email template: {e}")
        return False


# Templates de email pré-definidos
class EmailTemplates:
    """Templates de email para diferentes eventos."""

    @staticmethod
    def order_confirmation(
        customer_name: str,
        order_number: int,
        items: list,
        total: float,
        delivery_address: str,
    ) -> tuple[str, str, str]:
        """Retorna subject, body_text e body_html para confirmação de pedido."""
        subject = f"Pedido #{order_number} confirmado!"

        items_text = "\n".join([f"- {item}" for item in items])
        body_text = f"""
Olá {customer_name},

Seu pedido foi confirmado!

Pedido: #{order_number}
Itens:
{items_text}

Total: R$ {total:.2f}

Endereço de entrega:
{delivery_address}

Você receberá uma notificação quando a entrega estiver a caminho.

Obrigado pela preferência!
Gas Automation
        """.strip()

        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Pedido Confirmado!</h1>
        </div>
        <div class="content">
            <p>Olá <strong>{customer_name}</strong>,</p>
            <p>Seu pedido <strong>#{order_number}</strong> foi confirmado!</p>
            <h3>Itens:</h3>
            <ul>
                {"".join([f"<li>{item}</li>" for item in items])}
            </ul>
            <p><strong>Total: R$ {total:.2f}</strong></p>
            <h3>Endereço de entrega:</h3>
            <p>{delivery_address}</p>
        </div>
        <div class="footer">
            <p>Gas Automation - Seu gás com praticidade</p>
        </div>
    </div>
</body>
</html>
        """.strip()

        return subject, body_text, body_html

    @staticmethod
    def payment_confirmed(
        customer_name: str,
        order_number: int,
        amount: float,
        payment_method: str,
    ) -> tuple[str, str, str]:
        """Template para pagamento confirmado."""
        subject = f"Pagamento confirmado - Pedido #{order_number}"

        body_text = f"""
Olá {customer_name},

Seu pagamento foi confirmado!

Pedido: #{order_number}
Valor: R$ {amount:.2f}
Método: {payment_method}

Estamos preparando sua entrega!

Obrigado!
Gas Automation
        """.strip()

        body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #16a34a;">Pagamento Confirmado!</h2>
        <p>Olá <strong>{customer_name}</strong>,</p>
        <p>Seu pagamento foi confirmado com sucesso.</p>
        <ul>
            <li>Pedido: <strong>#{order_number}</strong></li>
            <li>Valor: <strong>R$ {amount:.2f}</strong></li>
            <li>Método: <strong>{payment_method}</strong></li>
        </ul>
        <p>Estamos preparando sua entrega!</p>
    </div>
</body>
</html>
        """.strip()

        return subject, body_text, body_html
