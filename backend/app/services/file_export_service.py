"""
Serviço de exportação de pedidos para arquivos (CSV/XML).

Alternativa ao firebird_export_service para cenários onde o banco Firebird
é somente leitura. Gera arquivos que podem ser importados manualmente no ERP.
"""

from __future__ import annotations

import csv
import io
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional, List
from uuid import UUID
from xml.etree import ElementTree as ET

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Formatos de exportação suportados."""
    CSV = "csv"
    XML = "xml"
    GASMASTER_TXT = "gasmaster_txt"  # Formato posicional para Gasmaster


class ExportStatus(str, Enum):
    """Status da exportação."""
    PENDING = "pending"
    EXPORTED = "exported"
    FAILED = "failed"


@dataclass
class ExportedOrderItem:
    """Item do pedido para exportação."""
    sequence: int
    product_code: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class ExportedOrder:
    """Dados do pedido formatados para exportação."""
    order_id: UUID
    order_number: int
    created_at: datetime
    delivered_at: Optional[datetime]
    total_amount: Decimal
    payment_method: Optional[str]
    tipo_operacao: str
    notes: Optional[str]

    # Cliente
    customer_id: UUID
    customer_name: str
    customer_phone: str
    customer_document: Optional[str]  # CPF/CNPJ
    customer_firebird_id: Optional[int]

    # Endereço
    delivery_street: Optional[str]
    delivery_number: Optional[str]
    delivery_complement: Optional[str]
    delivery_bairro: Optional[str]
    delivery_city: Optional[str]
    delivery_cep: Optional[str]

    # Itens
    items: List[ExportedOrderItem] = field(default_factory=list)


class FileExportService:
    """
    Serviço de exportação de pedidos para arquivos.

    Suporta múltiplos formatos: CSV, XML e formato posicional Gasmaster.
    """

    def __init__(self, export_dir: Optional[str] = None):
        """
        Inicializa o serviço.

        Args:
            export_dir: Diretório para salvar arquivos. Se None, usa diretório padrão.
        """
        self.export_dir = Path(export_dir) if export_dir else Path("exports")
        self._ensure_export_dir()

    def _ensure_export_dir(self) -> None:
        """Garante que o diretório de exportação existe."""
        self.export_dir.mkdir(parents=True, exist_ok=True)
        # Criar subdiretórios por formato
        (self.export_dir / "csv").mkdir(exist_ok=True)
        (self.export_dir / "xml").mkdir(exist_ok=True)
        (self.export_dir / "gasmaster").mkdir(exist_ok=True)

    async def _load_order(self, session: AsyncSession, order_id: UUID) -> Optional[Order]:
        """Carrega pedido com todas as relações."""
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def _load_orders_for_export(
        self,
        session: AsyncSession,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        exclude_exported: bool = True,
    ) -> List[Order]:
        """
        Carrega pedidos para exportação em lote.

        Args:
            status: Filtrar por status (ex: 'delivered')
            date_from: Data inicial
            date_to: Data final
            exclude_exported: Se True, exclui pedidos já exportados para arquivo
        """
        query = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )
        )

        filters = []

        if status:
            filters.append(Order.status == status)

        if date_from:
            filters.append(Order.created_at >= date_from)

        if date_to:
            filters.append(Order.created_at <= date_to)

        if exclude_exported:
            filters.append(Order.file_export_status.is_(None) | (Order.file_export_status != ExportStatus.EXPORTED.value))

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Order.created_at.asc())

        result = await session.execute(query)
        return list(result.scalars().all())

    def _order_to_export_data(self, order: Order) -> ExportedOrder:
        """Converte Order do banco para formato de exportação."""
        customer: Customer = order.customer

        # Extrair endereço
        addr = order.delivery_address or {}

        return ExportedOrder(
            order_id=order.id,
            order_number=order.order_number,
            created_at=order.created_at,
            delivered_at=order.delivered_at,
            total_amount=order.total_amount,
            payment_method=order.payment_method,
            tipo_operacao=order.tipo_operacao,
            notes=order.notes,

            customer_id=customer.id,
            customer_name=customer.name,
            customer_phone=customer.phone,
            customer_document=getattr(customer, 'document', None),
            customer_firebird_id=customer.firebird_id,

            delivery_street=addr.get('street') or addr.get('logradouro'),
            delivery_number=addr.get('number') or addr.get('numero'),
            delivery_complement=addr.get('complement') or addr.get('complemento'),
            delivery_bairro=addr.get('bairro') or order.delivery_bairro,
            delivery_city=addr.get('city') or addr.get('cidade', 'Curitiba'),
            delivery_cep=addr.get('cep'),

            items=[
                ExportedOrderItem(
                    sequence=idx + 1,
                    product_code=item.product_code,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
                for idx, item in enumerate(order.items)
            ],
        )

    # ==================== CSV Export ====================

    def generate_csv(self, orders: List[ExportedOrder]) -> str:
        """
        Gera conteúdo CSV dos pedidos.

        Formato: Um arquivo com cabeçalho e uma linha por item de pedido.
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Cabeçalho
        writer.writerow([
            'PEDIDO_NUM',
            'DATA_PEDIDO',
            'DATA_ENTREGA',
            'CLIENTE_ID_FIREBIRD',
            'CLIENTE_NOME',
            'CLIENTE_TELEFONE',
            'CLIENTE_DOCUMENTO',
            'ENDERECO_RUA',
            'ENDERECO_NUMERO',
            'ENDERECO_COMPLEMENTO',
            'ENDERECO_BAIRRO',
            'ENDERECO_CIDADE',
            'ENDERECO_CEP',
            'TIPO_OPERACAO',
            'FORMA_PAGAMENTO',
            'ITEM_SEQ',
            'PRODUTO_CODIGO',
            'PRODUTO_NOME',
            'QUANTIDADE',
            'PRECO_UNITARIO',
            'SUBTOTAL',
            'TOTAL_PEDIDO',
            'OBSERVACOES',
        ])

        # Dados
        for order in orders:
            for item in order.items:
                writer.writerow([
                    order.order_number,
                    order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else '',
                    order.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if order.delivered_at else '',
                    order.customer_firebird_id or '',
                    order.customer_name,
                    order.customer_phone,
                    order.customer_document or '',
                    order.delivery_street or '',
                    order.delivery_number or '',
                    order.delivery_complement or '',
                    order.delivery_bairro or '',
                    order.delivery_city or '',
                    order.delivery_cep or '',
                    order.tipo_operacao.upper(),
                    order.payment_method or '',
                    item.sequence,
                    item.product_code,
                    item.product_name,
                    item.quantity,
                    f'{item.unit_price:.2f}',
                    f'{item.subtotal:.2f}',
                    f'{order.total_amount:.2f}',
                    (order.notes or '').replace('\n', ' ').replace(';', ',')[:200],
                ])

        return output.getvalue()

    def generate_csv_summary(self, orders: List[ExportedOrder]) -> str:
        """
        Gera CSV resumido (uma linha por pedido, sem detalhes de itens).
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            'PEDIDO_NUM',
            'DATA_PEDIDO',
            'DATA_ENTREGA',
            'CLIENTE_ID_FIREBIRD',
            'CLIENTE_NOME',
            'CLIENTE_TELEFONE',
            'BAIRRO',
            'TIPO_OPERACAO',
            'FORMA_PAGAMENTO',
            'QTD_ITENS',
            'TOTAL',
        ])

        for order in orders:
            writer.writerow([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else '',
                order.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if order.delivered_at else '',
                order.customer_firebird_id or '',
                order.customer_name,
                order.customer_phone,
                order.delivery_bairro or '',
                order.tipo_operacao.upper(),
                order.payment_method or '',
                len(order.items),
                f'{order.total_amount:.2f}',
            ])

        return output.getvalue()

    # ==================== XML Export ====================

    def generate_xml(self, orders: List[ExportedOrder]) -> str:
        """
        Gera conteúdo XML dos pedidos.

        Formato compatível com importação em ERPs.
        """
        root = ET.Element('pedidos')
        root.set('gerado_em', datetime.now(timezone.utc).isoformat())
        root.set('total_pedidos', str(len(orders)))

        for order in orders:
            pedido_el = ET.SubElement(root, 'pedido')
            pedido_el.set('numero', str(order.order_number))

            # Dados gerais
            ET.SubElement(pedido_el, 'data_pedido').text = (
                order.created_at.isoformat() if order.created_at else ''
            )
            ET.SubElement(pedido_el, 'data_entrega').text = (
                order.delivered_at.isoformat() if order.delivered_at else ''
            )
            ET.SubElement(pedido_el, 'tipo_operacao').text = order.tipo_operacao
            ET.SubElement(pedido_el, 'forma_pagamento').text = order.payment_method or ''
            ET.SubElement(pedido_el, 'total').text = f'{order.total_amount:.2f}'
            ET.SubElement(pedido_el, 'observacoes').text = order.notes or ''

            # Cliente
            cliente_el = ET.SubElement(pedido_el, 'cliente')
            ET.SubElement(cliente_el, 'id_firebird').text = str(order.customer_firebird_id or '')
            ET.SubElement(cliente_el, 'nome').text = order.customer_name
            ET.SubElement(cliente_el, 'telefone').text = order.customer_phone
            ET.SubElement(cliente_el, 'documento').text = order.customer_document or ''

            # Endereço
            endereco_el = ET.SubElement(pedido_el, 'endereco')
            ET.SubElement(endereco_el, 'rua').text = order.delivery_street or ''
            ET.SubElement(endereco_el, 'numero').text = order.delivery_number or ''
            ET.SubElement(endereco_el, 'complemento').text = order.delivery_complement or ''
            ET.SubElement(endereco_el, 'bairro').text = order.delivery_bairro or ''
            ET.SubElement(endereco_el, 'cidade').text = order.delivery_city or ''
            ET.SubElement(endereco_el, 'cep').text = order.delivery_cep or ''

            # Itens
            itens_el = ET.SubElement(pedido_el, 'itens')
            for item in order.items:
                item_el = ET.SubElement(itens_el, 'item')
                item_el.set('sequencia', str(item.sequence))
                ET.SubElement(item_el, 'codigo').text = item.product_code
                ET.SubElement(item_el, 'nome').text = item.product_name
                ET.SubElement(item_el, 'quantidade').text = str(item.quantity)
                ET.SubElement(item_el, 'preco_unitario').text = f'{item.unit_price:.2f}'
                ET.SubElement(item_el, 'subtotal').text = f'{item.subtotal:.2f}'

        # Formatar XML com indentação
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    # ==================== Gasmaster TXT Export ====================

    def generate_gasmaster_txt(self, orders: List[ExportedOrder]) -> str:
        """
        Gera arquivo TXT no formato posicional para importação no Gasmaster.

        Formato:
        - Linha tipo H (Header): dados do pedido
        - Linha tipo I (Item): itens do pedido

        Campos posicionais com tamanho fixo.
        """
        lines = []

        for order in orders:
            # Header (H) - 200 caracteres
            # Posições: TIPO(1) | PEDIDO(10) | DATA(10) | CLIENTE_ID(10) | CLIENTE_NOME(60) | TELEFONE(15) | BAIRRO(40) | TIPO_OP(10) | PAGTO(15) | TOTAL(12) | OBS(17)
            header = (
                'H'  # Tipo registro
                + str(order.order_number).zfill(10)  # Número pedido
                + (order.created_at.strftime('%Y-%m-%d') if order.created_at else '          ')  # Data
                + str(order.customer_firebird_id or '').zfill(10)  # ID Firebird cliente
                + (order.customer_name or '')[:60].ljust(60)  # Nome cliente
                + (order.customer_phone or '')[:15].ljust(15)  # Telefone
                + (order.delivery_bairro or '')[:40].ljust(40)  # Bairro
                + (order.tipo_operacao or '')[:10].upper().ljust(10)  # Tipo operação
                + (order.payment_method or '')[:15].ljust(15)  # Forma pagamento
                + f'{order.total_amount:012.2f}'.replace('.', '')  # Total (centavos)
                + (order.notes or '').replace('\n', ' ')[:17].ljust(17)  # Obs truncada
            )
            lines.append(header)

            # Items (I) - 100 caracteres cada
            # Posições: TIPO(1) | PEDIDO(10) | SEQ(3) | CODIGO(10) | NOME(40) | QTD(6) | PRECO(12) | SUBTOTAL(12) | PADDING(6)
            for item in order.items:
                item_line = (
                    'I'  # Tipo registro
                    + str(order.order_number).zfill(10)  # Número pedido
                    + str(item.sequence).zfill(3)  # Sequência
                    + (item.product_code or '')[:10].ljust(10)  # Código produto
                    + (item.product_name or '')[:40].ljust(40)  # Nome produto
                    + str(item.quantity).zfill(6)  # Quantidade
                    + f'{item.unit_price:012.2f}'.replace('.', '')  # Preço (centavos)
                    + f'{item.subtotal:012.2f}'.replace('.', '')  # Subtotal (centavos)
                    + ' ' * 6  # Padding
                )
                lines.append(item_line)

        return '\n'.join(lines)

    # ==================== Export Methods ====================

    async def export_order(
        self,
        order_id: UUID,
        format: ExportFormat = ExportFormat.CSV,
    ) -> Tuple[str, str]:
        """
        Exporta um único pedido.

        Returns:
            Tuple (conteúdo, nome_arquivo)
        """
        async with AsyncSessionLocal() as session:
            order = await self._load_order(session, order_id)
            if not order:
                raise ValueError(f"Pedido {order_id} não encontrado")

            export_data = self._order_to_export_data(order)
            return self._generate_export([export_data], format, single=True)

    async def export_orders_batch(
        self,
        format: ExportFormat = ExportFormat.CSV,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        exclude_exported: bool = True,
        save_to_file: bool = True,
        mark_as_exported: bool = True,
    ) -> Tuple[str, str, int]:
        """
        Exporta lote de pedidos.

        Args:
            format: Formato de exportação
            status: Filtrar por status
            date_from: Data inicial
            date_to: Data final
            exclude_exported: Excluir já exportados
            save_to_file: Salvar arquivo no disco
            mark_as_exported: Marcar pedidos como exportados no banco

        Returns:
            Tuple (conteúdo, nome_arquivo, quantidade_pedidos)
        """
        async with AsyncSessionLocal() as session:
            orders = await self._load_orders_for_export(
                session,
                status=status,
                date_from=date_from,
                date_to=date_to,
                exclude_exported=exclude_exported,
            )

            if not orders:
                raise ValueError("Nenhum pedido encontrado para exportação")

            export_data = [self._order_to_export_data(o) for o in orders]
            content, filename = self._generate_export(export_data, format, single=False)

            # Salvar arquivo
            if save_to_file:
                filepath = self._save_file(content, filename, format)
                logger.info(f"Arquivo exportado: {filepath}")

            # Marcar como exportados
            if mark_as_exported:
                for order in orders:
                    order.file_export_status = ExportStatus.EXPORTED.value
                    order.file_exported_at = datetime.now(timezone.utc)
                await session.commit()

            return content, filename, len(orders)

    def _generate_export(
        self,
        orders: List[ExportedOrder],
        format: ExportFormat,
        single: bool = False,
    ) -> Tuple[str, str]:
        """Gera conteúdo e nome do arquivo."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format == ExportFormat.CSV:
            content = self.generate_csv(orders)
            suffix = f"pedido_{orders[0].order_number}" if single else f"pedidos_{timestamp}"
            filename = f"{suffix}.csv"

        elif format == ExportFormat.XML:
            content = self.generate_xml(orders)
            suffix = f"pedido_{orders[0].order_number}" if single else f"pedidos_{timestamp}"
            filename = f"{suffix}.xml"

        elif format == ExportFormat.GASMASTER_TXT:
            content = self.generate_gasmaster_txt(orders)
            suffix = f"pedido_{orders[0].order_number}" if single else f"gasmaster_{timestamp}"
            filename = f"{suffix}.txt"

        else:
            raise ValueError(f"Formato não suportado: {format}")

        return content, filename

    def _save_file(self, content: str, filename: str, format: ExportFormat) -> Path:
        """Salva arquivo no diretório apropriado."""
        if format == ExportFormat.CSV:
            subdir = "csv"
        elif format == ExportFormat.XML:
            subdir = "xml"
        else:
            subdir = "gasmaster"

        filepath = self.export_dir / subdir / filename
        filepath.write_text(content, encoding='utf-8')
        return filepath

    def list_exported_files(
        self,
        format: Optional[ExportFormat] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        Lista arquivos exportados.

        Returns:
            Lista de dicts com info dos arquivos.
        """
        files = []

        subdirs = ["csv", "xml", "gasmaster"] if not format else [
            "csv" if format == ExportFormat.CSV else
            "xml" if format == ExportFormat.XML else
            "gasmaster"
        ]

        for subdir in subdirs:
            dir_path = self.export_dir / subdir
            if not dir_path.exists():
                continue

            for f in sorted(dir_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file():
                    stat = f.stat()
                    files.append({
                        "name": f.name,
                        "path": str(f),
                        "format": subdir,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })

                if len(files) >= limit:
                    break

        return files[:limit]


# Instância global
file_export_service = FileExportService()


# ==================== Funções de conveniência ====================

async def export_order_to_file(
    order_id: UUID,
    format: ExportFormat = ExportFormat.CSV,
) -> Tuple[str, str]:
    """Exporta pedido individual para arquivo."""
    return await file_export_service.export_order(order_id, format)


async def export_delivered_orders_to_file(
    format: ExportFormat = ExportFormat.CSV,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Tuple[str, str, int]:
    """Exporta pedidos entregues para arquivo."""
    return await file_export_service.export_orders_batch(
        format=format,
        status=OrderStatus.DELIVERED.value,
        date_from=date_from,
        date_to=date_to,
    )
