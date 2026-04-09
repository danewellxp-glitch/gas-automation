from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageTemplate, ListFlowable, ListItem, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
import os

BRAND_NAVY = colors.HexColor('#14283b')
BRAND_ORANGE = colors.HexColor('#f54e00')
BRAND_YELLOW = colors.HexColor('#f7c900')
GRAY_LIGHT = colors.HexColor('#f3f4f6')
GRAY_DARK = colors.HexColor('#4b5563')

def create_header(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND_NAVY)
    canvas.rect(0, A4[1] - 1.5*inch, A4[0], 1.5*inch, fill=1, stroke=0)
    
    try:
        logo_path = "/home/daniel/gas-automation/frontend/public/logo_sistema.png"
        if os.path.exists(logo_path):
            canvas.drawImage(logo_path, 0.5*inch, A4[1] - 1.2*inch, width=2.5*inch, height=0.9*inch, preserveAspectRatio=True, mask='auto')
        else:
            raise Exception("No logo")
    except Exception:
        canvas.setFont('Helvetica-Bold', 24)
        canvas.setFillColor(colors.white)
        canvas.drawString(0.5*inch, A4[1] - 0.8*inch, "Gasmaster")
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(BRAND_YELLOW)
        canvas.drawString(0.5*inch, A4[1] - 1.05*inch, "DISTRIBUIDORA DE GÁS")
        
    canvas.setFont('Helvetica-Bold', 18)
    canvas.setFillColor(colors.white)
    canvas.drawString(A4[0] - 4.5*inch, A4[1] - 0.7*inch, "Documentação de BI")
    
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(BRAND_YELLOW)
    canvas.drawString(A4[0] - 4.5*inch, A4[1] - 0.9*inch, "Lógica Preditiva de Logística")
    
    canvas.setStrokeColor(BRAND_ORANGE)
    canvas.setLineWidth(3)
    canvas.line(0, A4[1] - 1.5*inch, A4[0], A4[1] - 1.5*inch)
    canvas.restoreState()

def create_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(GRAY_LIGHT)
    canvas.rect(0, 0, A4[0], 0.6*inch, fill=1, stroke=0)
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(GRAY_DARK)
    canvas.drawString(0.5*inch, 0.25*inch, "MERCURYGAS | BUSINESS INTELLIGENCE")
    page_num = f"Página {doc.page}"
    canvas.drawRightString(A4[0] - 0.5*inch, 0.25*inch, page_num)
    canvas.restoreState()

def build_graphical_pdf(filename):
    doc = SimpleDocTemplate(
        filename, 
        pagesize=A4,
        rightMargin=0.8*inch, 
        leftMargin=0.8*inch,
        topMargin=2.0*inch, 
        bottomMargin=1.0*inch
    )
    
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='First', frames=frame, onPage=create_header, onPageEnd=create_footer)
    doc.addPageTemplates([template])
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        name='ModernTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=15,
        textColor=BRAND_NAVY,
        fontName='Helvetica-Bold'
    )
    
    h2_style = ParagraphStyle(
        name='ModernH2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=10,
        textColor=BRAND_NAVY,
        fontName='Helvetica-Bold',
        borderPadding=(0, 0, 4, 0),
        borderColor=BRAND_ORANGE,
        borderWidth=1,
        borderRadius=0,
    )
    
    normal_style = ParagraphStyle(
        name='ModernNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        textColor=GRAY_DARK,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    intro_style = ParagraphStyle(
        name='IntroNormal',
        parent=normal_style,
        fontSize=11,
        textColor=BRAND_NAVY,
        fontName='Helvetica-Oblique'
    )
    
    bullet_style = ParagraphStyle(
        name='ModernBullet',
        parent=normal_style,
        spaceAfter=6,
        leftIndent=15
    )

    story = []
    
    # Title
    story.append(Paragraph("Lógica de Negócios e BI: Logística e Estoque", title_style))
    story.append(Paragraph("Este documento oficializa o fluxograma lógico e as regras de Business Intelligence (BI) para o sistema de fechamento preditivo de caixa e rastreio de vasilhames da operação Gasmaster.", intro_style))
    story.append(Spacer(1, 0.2 * inch))

    # Bloc 1
    story.append(Paragraph("1. O Conceito de Estoque Unificado", h2_style))
    story.append(Paragraph("Em uma distribuidora de grande porte (como para operações de +9.000 pedidos/dia), o vasilhame é o principal ativo circulante. O estoque unificado garante que todos os perfis falem a mesma língua:", normal_style))
    b1 = [
        ListItem(Paragraph("<b>Atendente:</b> Visualiza vazios e cheios da base para garantir prontidão de venda.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Responsável de Pátio:</b> Realiza as cargas logísticas retirando vasilhames do Galpão e enviando a campo.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Financeiro:</b> Visualiza o inventário como dinheiro; Qualquer perda computa fluxo de caixa automatizado.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b1, bulletType='bullet', bulletFontName='Helvetica'))

    # Bloc 2
    story.append(Paragraph("2. Montagem e Saída de Carga", h2_style))
    story.append(Paragraph("As antigas planilhas de prancheta são substituídas pelo módulo de 'Cargas'.", normal_style))
    b2 = [
        ListItem(Paragraph("Sempre que um motorista é abastecido (ex: 50 botijões P13), a plataforma subtrai o montante de Cheios da base.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("A carga vai integralmente para o estoque <i>'Em Campo'</i> alocado exclusivamente no veículo do colaborador responsável.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b2, bulletType='bullet', bulletFontName='Helvetica'))

    # Bloc 3
    story.append(Paragraph("3. A Inteligência Preditiva no Trajeto", h2_style))
    story.append(Paragraph("Ao longo do dia de trabalho, o motorista não preenche rotinas manuais de inventário. O banco de dados consolida e prediz o inventário dele baseado na telemetria de pedidos do painel central.", normal_style))
    b3 = [
        ListItem(Paragraph("<b>Venda Padrão (Com Troca):</b> Cliente recebe 1 Cheio e defere 1 Vazio. O saldo 'Em Campo' cai para 49 Cheios, cresce para 1 Vazio.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Venda Direta (Sem Troca):</b> Identifica as compras diretas. Entregue 1 Cheio, nenhum Vazio retornado.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b3, bulletType='bullet', bulletFontName='Helvetica'))

    # Bloc 4
    story.append(Paragraph("4. Retorno e Fechamento à Prova de Fugas", h2_style))
    story.append(Paragraph("A eliminação total de 'vazamento invisível' e desvio de patrimônio ocorre na auditoria reversa de carga no fechamento de caixa.", normal_style))
    b4 = [
        ListItem(Paragraph("Ao retornar, o BI acusa de forma exata: <i>'A Load 159 deve possuir 28 Cheios e 20 Vazios, junto com R$ 2.400 em lastro financeiro'</i>.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("Em caso de inconsistências (ex: contagem detecta falto de 1 Vazio), o lançamento imediato ativa o balancete de 'Perdas de Vasilhames'.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b4, bulletType='bullet', bulletFontName='Helvetica'))

    doc.build(story)

if __name__ == "__main__":
    build_graphical_pdf("/home/daniel/Documentacao_BI_Logistica_Gasmaster.pdf")
    print("PDF Generated successfully.")
