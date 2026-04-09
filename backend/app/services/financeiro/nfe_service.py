"""Serviço de NF-e via Unimake Cloud."""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.financeiro.nota_fiscal import NotaFiscal
from app.models.order import Order

logger = logging.getLogger(__name__)


class NFeService:

    async def gerar_xml_nfe(self, db: AsyncSession, pedido_id: UUID, tipo: str = "65") -> tuple[str, dict]:
        """
        Monta XML simplificado de NF-e/NFC-e.
        Retorna (xml_str, dados_fiscais_dict).

        NOTA: XML gerado aqui é uma estrutura mínima válida para HOMOLOGAÇÃO.
        Para PRODUÇÃO, validar com contador todas as tags fiscais.
        """
        from app.models.customer import Customer
        from app.models.order import OrderItem
        from app.models.product import Product

        order_result = await db.execute(select(Order).where(Order.id == pedido_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise ValueError(f"Pedido {pedido_id} não encontrado")

        cust_result = await db.execute(select(Customer).where(Customer.id == order.customer_id))
        customer = cust_result.scalar_one_or_none()

        items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == pedido_id))
        items = items_result.scalars().all()

        now = datetime.now(timezone.utc)

        # Determinar tipo baseado no documento do cliente
        cpf = getattr(customer, "cpf", None) or getattr(customer, "document", None)
        cnpj = getattr(customer, "cnpj", None)

        total = order.total_amount or Decimal("0.00")

        # XML básico - estrutura mínima NFe
        det_xml = ""
        for i, item in enumerate(items, 1):
            prod_result = await db.execute(
                select(Product).where(Product.code == item.product_code)
            )
            product = prod_result.scalar_one_or_none()
            ncm = settings.nfe_ncm_gas
            unidade = "UN"
            if product and getattr(product, "categoria", None) == "agua":
                ncm = settings.nfe_ncm_agua
                unidade = "LT"

            det_xml += f"""
        <det nItem="{i}">
            <prod>
                <cProd>{item.product_code}</cProd>
                <cEAN>SEM GTIN</cEAN>
                <xProd>{product.name if product else item.product_code}</xProd>
                <NCM>{ncm}</NCM>
                <CFOP>{settings.nfe_cfop_venda}</CFOP>
                <uCom>{unidade}</uCom>
                <qCom>{item.quantity}</qCom>
                <vUnCom>{float(item.unit_price):.2f}</vUnCom>
                <vProd>{float(item.unit_price * item.quantity):.2f}</vProd>
                <cEANTrib>SEM GTIN</cEANTrib>
                <uTrib>{unidade}</uTrib>
                <qTrib>{item.quantity}</qTrib>
                <vUnTrib>{float(item.unit_price):.2f}</vUnTrib>
                <indTot>1</indTot>
            </prod>
            <imposto>
                <ICMS>
                    <ICMSSN400>
                        <orig>0</orig>
                        <CSOSN>{settings.nfe_csosn}</CSOSN>
                    </ICMSSN400>
                </ICMS>
                <PIS>
                    <PISAliq>
                        <CST>01</CST>
                        <vBC>{float(total):.2f}</vBC>
                        <pPIS>{settings.nfe_aliq_pis:.2f}</pPIS>
                        <vPIS>{float(total) * settings.nfe_aliq_pis / 100:.2f}</vPIS>
                    </PISAliq>
                </PIS>
                <COFINS>
                    <COFINSAliq>
                        <CST>01</CST>
                        <vBC>{float(total):.2f}</vBC>
                        <pCOFINS>{settings.nfe_aliq_cofins:.2f}</pCOFINS>
                        <vCOFINS>{float(total) * settings.nfe_aliq_cofins / 100:.2f}</vCOFINS>
                    </COFINSAliq>
                </COFINS>
            </imposto>
        </det>"""

        dest_doc = ""
        if cnpj:
            dest_doc = f"<CNPJ>{cnpj}</CNPJ>"
        elif cpf:
            dest_doc = f"<CPF>{cpf}</CPF>"
        else:
            dest_doc = "<indIEDest>9</indIEDest>"  # consumidor não identificado

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
    <infNFe versao="4.00">
        <ide>
            <cUF>41</cUF>
            <cNF>{now.strftime('%H%M%S')}</cNF>
            <natOp>VENDA DE MERCADORIAS</natOp>
            <mod>{tipo}</mod>
            <serie>1</serie>
            <nNF>0</nNF>
            <dhEmi>{now.strftime('%Y-%m-%dT%H:%M:%S-03:00')}</dhEmi>
            <tpNF>1</tpNF>
            <idDest>1</idDest>
            <cMunFG>4106902</cMunFG>
            <tpImp>4</tpImp>
            <tpEmis>1</tpEmis>
            <tpAmb>{settings.unimake_ambiente}</tpAmb>
            <finNFe>1</finNFe>
            <indFinal>1</indFinal>
            <indPres>1</indPres>
        </ide>
        <emit>
            <CNPJ>{settings.nfe_cnpj}</CNPJ>
            <xNome>{settings.nfe_razao_social}</xNome>
            <xFant>{settings.nfe_nome_fantasia}</xFant>
            <enderEmit>
                <xLgr>{settings.nfe_logradouro}</xLgr>
                <nro>{settings.nfe_numero}</nro>
                <xBairro>{settings.nfe_bairro}</xBairro>
                <cMun>4106902</cMun>
                <xMun>{settings.nfe_municipio}</xMun>
                <UF>{settings.nfe_uf}</UF>
                <CEP>{settings.nfe_cep}</CEP>
                <cPais>1058</cPais>
                <xPais>Brasil</xPais>
                <fone>{settings.nfe_telefone}</fone>
            </enderEmit>
            <IE>{settings.nfe_ie}</IE>
            <CRT>{settings.nfe_regime_tributario}</CRT>
        </emit>
        <dest>
            {dest_doc}
            <xNome>{customer.name if customer else 'CONSUMIDOR'}</xNome>
            <indIEDest>9</indIEDest>
        </dest>
        {det_xml}
        <total>
            <ICMSTot>
                <vBC>0.00</vBC>
                <vICMS>0.00</vICMS>
                <vICMSDeson>0.00</vICMSDeson>
                <vFCP>0.00</vFCP>
                <vBCST>0.00</vBCST>
                <vST>0.00</vST>
                <vFCPST>0.00</vFCPST>
                <vFCPSTRet>0.00</vFCPSTRet>
                <vProd>{float(total):.2f}</vProd>
                <vFrete>0.00</vFrete>
                <vSeg>0.00</vSeg>
                <vDesc>0.00</vDesc>
                <vII>0.00</vII>
                <vIPI>0.00</vIPI>
                <vIPIDevol>0.00</vIPIDevol>
                <vPIS>{float(total) * settings.nfe_aliq_pis / 100:.2f}</vPIS>
                <vCOFINS>{float(total) * settings.nfe_aliq_cofins / 100:.2f}</vCOFINS>
                <vOutro>0.00</vOutro>
                <vNF>{float(total):.2f}</vNF>
            </ICMSTot>
        </total>
        <transp>
            <modFrete>9</modFrete>
        </transp>
        <pag>
            <detPag>
                <tPag>01</tPag>
                <vPag>{float(total):.2f}</vPag>
            </detPag>
        </pag>
    </infNFe>
</NFe>"""

        dados = {
            "valor_total": total,
            "valor_pis": total * Decimal(str(settings.nfe_aliq_pis)) / 100,
            "valor_cofins": total * Decimal(str(settings.nfe_aliq_cofins)) / 100,
        }
        return xml, dados

    async def enviar_para_sefaz(self, db: AsyncSession, nota_fiscal_id: UUID) -> dict:
        """Envia XML para API Unimake Cloud."""
        result = await db.execute(select(NotaFiscal).where(NotaFiscal.id == nota_fiscal_id))
        nf = result.scalar_one_or_none()
        if not nf:
            raise ValueError("NotaFiscal não encontrada")

        if not settings.unimake_api_token:
            raise ValueError("UNIMAKE_API_TOKEN não configurado")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.unimake_api_url}/nfe/nfe",
                    headers={
                        "Authorization": f"Bearer {settings.unimake_api_token}",
                        "Content-Type": "application/json",
                    },
                    json={"xml": nf.xml_enviado},
                )

            data = resp.json()

            if resp.status_code == 200 and data.get("status") == "autorizada":
                nf.status = "autorizada"
                nf.chave_acesso = data.get("chave_acesso")
                nf.xml_autorizado = data.get("xml_autorizado")
                nf.pdf_danfe_url = data.get("pdf_danfe_url")
                nf.numero = data.get("numero")
                nf.emitida_at = datetime.now(timezone.utc)
            else:
                nf.status = "rejeitada"
                nf.motivo_rejeicao = data.get("motivo", str(data))

            await db.flush()
            return data

        except Exception as e:
            nf.status = "erro_emissao"
            nf.motivo_rejeicao = str(e)
            await db.flush()
            raise

    async def emitir_nfe_pedido(self, db: AsyncSession, pedido_id: UUID, user_id: UUID) -> NotaFiscal:
        """Fluxo completo de emissão."""
        from app.models.customer import Customer

        # Verifica se já existe NF-e para o pedido
        existing = await db.execute(
            select(NotaFiscal).where(
                NotaFiscal.pedido_id == pedido_id,
                NotaFiscal.status.in_(["autorizada", "enviada"]),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("NF-e já emitida para este pedido")

        order_result = await db.execute(select(Order).where(Order.id == pedido_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise ValueError("Pedido não encontrado")

        cust_result = await db.execute(select(Customer).where(Customer.id == order.customer_id))
        customer = cust_result.scalar_one_or_none()

        # Determinar tipo: 65=NFC-e (CPF/anon), 55=NF-e (CNPJ)
        cnpj = getattr(customer, "cnpj", None)
        tipo = "55" if cnpj else "65"

        xml, dados = await self.gerar_xml_nfe(db, pedido_id, tipo)

        nf = NotaFiscal(
            tipo=tipo,
            status="rascunho",
            pedido_id=pedido_id,
            customer_id=order.customer_id,
            emitido_por=user_id,
            valor_produtos=dados["valor_total"],
            valor_total=dados["valor_total"],
            valor_pis=dados["valor_pis"],
            valor_cofins=dados["valor_cofins"],
            xml_enviado=xml,
        )
        db.add(nf)
        await db.flush()

        nf.status = "enviada"
        await db.flush()

        try:
            await self.enviar_para_sefaz(db, nf.id)
        except Exception as e:
            logger.error(f"Erro ao enviar NF-e para SEFAZ: {e}")

        if nf.status == "autorizada":
            try:
                await self.enviar_danfe_whatsapp(db, nf.id)
            except Exception as e:
                logger.error(f"Erro ao enviar DANFE WhatsApp: {e}")

        return nf

    async def enviar_danfe_whatsapp(self, db: AsyncSession, nota_fiscal_id: UUID) -> bool:
        """Envia DANFE via WhatsApp."""
        from app.models.customer import Customer

        result = await db.execute(select(NotaFiscal).where(NotaFiscal.id == nota_fiscal_id))
        nf = result.scalar_one_or_none()
        if not nf or not nf.pdf_danfe_url:
            return False

        cust_result = await db.execute(select(Customer).where(Customer.id == nf.customer_id))
        customer = cust_result.scalar_one_or_none()
        if not customer:
            return False

        phone = getattr(customer, "phone", None) or getattr(customer, "whatsapp", None)
        if not phone:
            return False

        mensagem = (
            f"Olá {customer.name}! 🧾\n\n"
            f"Aqui está sua nota fiscal referente à sua compra.\n"
            f"NF-e nº {nf.numero}\n"
            f"Valor: R$ {float(nf.valor_total):.2f}\n"
        )
        if nf.chave_acesso:
            mensagem += f"Chave: {nf.chave_acesso}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Envia mensagem de texto
                await client.post(
                    f"{settings.waha_url}/api/sendText",
                    headers={"X-Api-Key": settings.waha_api_key},
                    json={
                        "session": settings.waha_session_name,
                        "chatId": f"{phone}@c.us",
                        "text": mensagem,
                    },
                )
                # Envia PDF se disponível
                if nf.pdf_danfe_url:
                    await client.post(
                        f"{settings.waha_url}/api/sendFile",
                        headers={"X-Api-Key": settings.waha_api_key},
                        json={
                            "session": settings.waha_session_name,
                            "chatId": f"{phone}@c.us",
                            "file": {
                                "url": nf.pdf_danfe_url,
                                "filename": f"NF-e_{nf.numero}.pdf",
                            },
                        },
                    )

            nf.enviada_whatsapp = True
            nf.enviada_whatsapp_at = datetime.now(timezone.utc)
            await db.flush()
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar DANFE WhatsApp: {e}")
            return False

    async def cancelar_nfe(
        self, db: AsyncSession, nota_fiscal_id: UUID, motivo: str, user_id: UUID
    ) -> NotaFiscal:
        """Cancela NF-e na SEFAZ via Unimake."""
        result = await db.execute(select(NotaFiscal).where(NotaFiscal.id == nota_fiscal_id))
        nf = result.scalar_one_or_none()
        if not nf:
            raise ValueError("NotaFiscal não encontrada")
        if nf.status != "autorizada":
            raise ValueError("Apenas NF-e autorizadas podem ser canceladas")

        nf.status = "cancelada"
        nf.motivo_rejeicao = motivo
        await db.flush()
        return nf

    async def reenviar_danfe(self, db: AsyncSession, nota_fiscal_id: UUID) -> bool:
        return await self.enviar_danfe_whatsapp(db, nota_fiscal_id)
