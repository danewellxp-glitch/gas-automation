"""
PDF Export Service.

Gera relatórios em PDF usando ReportLab.
"""
import logging
from io import BytesIO
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFExportService:
    """Serviço para exportar relatórios em PDF."""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab não disponível. Instale com: pip install reportlab")
    
    def export_report(
        self,
        report_type: str,
        data: Dict[str, Any],
        title: Optional[str] = None,
    ) -> BytesIO:
        """
        Gera PDF de um relatório.
        
        Args:
            report_type: Tipo do relatório (financial, operational, performance, etc.)
            data: Dados do relatório
            title: Título do relatório
            
        Returns:
            BytesIO com conteúdo do PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab não está instalado. Instale com: pip install reportlab")
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )
        
        # Conteúdo
        story = []
        
        # Título
        if title:
            story.append(Paragraph(title, title_style))
        else:
            story.append(Paragraph(f"Relatório {report_type.title()}", title_style))
        
        story.append(Spacer(1, 0.2 * inch))
        
        # Data de geração
        story.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.3 * inch))
        
        # Conteúdo específico por tipo
        if report_type == "financial":
            story.extend(self._build_financial_report(data, styles))
        elif report_type == "operational":
            story.extend(self._build_operational_report(data, styles))
        elif report_type == "performance":
            story.extend(self._build_performance_report(data, styles))
        else:
            story.append(Paragraph(f"Tipo de relatório '{report_type}' não suportado.", styles['Normal']))
        
        # Construir PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def _build_financial_report(self, data: Dict[str, Any], styles) -> List:
        """Constrói relatório financeiro."""
        elements = []
        
        # Resumo financeiro
        elements.append(Paragraph("Resumo Financeiro", styles['Heading2']))
        elements.append(Spacer(1, 0.2 * inch))
        
        financial_data = [
            ['Métrica', 'Valor'],
            ['Faturamento Total', f"R$ {data.get('total_revenue', 0):,.2f}"],
            ['Pagamentos Recebidos', f"R$ {data.get('payments_received', 0):,.2f}"],
            ['Ticket Médio', f"R$ {data.get('avg_ticket', 0):,.2f}"],
            ['Pedidos Entregues', str(data.get('delivered_count', 0))],
        ]
        
        table = Table(financial_data, colWidths=[4 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        
        return elements
    
    def _build_operational_report(self, data: Dict[str, Any], styles) -> List:
        """Constrói relatório operacional."""
        elements = []
        
        elements.append(Paragraph("Resumo Operacional", styles['Heading2']))
        elements.append(Spacer(1, 0.2 * inch))
        
        operational_data = [
            ['Métrica', 'Valor'],
            ['Total de Pedidos', str(data.get('total_orders', 0))],
            ['Pedidos Pendentes', str(data.get('pending_count', 0))],
            ['Pedidos Entregues', str(data.get('delivered_count', 0))],
            ['Pedidos Cancelados', str(data.get('cancelled_count', 0))],
            ['Taxa de Conversão', f"{data.get('conversion_rate', 0):.1f}%"],
        ]
        
        table = Table(operational_data, colWidths=[4 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        
        return elements
    
    def _build_performance_report(self, data: Dict[str, Any], styles) -> List:
        """Constrói relatório de performance."""
        elements = []
        
        elements.append(Paragraph("Resumo de Performance", styles['Heading2']))
        elements.append(Spacer(1, 0.2 * inch))
        
        performance_data = [
            ['Métrica', 'Valor'],
            ['Tempo Médio de Resposta', f"{data.get('avg_response_time', 0):.1f} min"],
            ['Pedidos por Operador', str(data.get('orders_per_operator', 0))],
            ['Taxa de Aprovação', f"{data.get('approval_rate', 0):.1f}%"],
        ]
        
        table = Table(performance_data, colWidths=[4 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        
        return elements


# Instância global
pdf_export_service = PDFExportService()