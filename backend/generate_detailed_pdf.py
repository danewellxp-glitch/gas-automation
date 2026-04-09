from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageTemplate, Image, Table, TableStyle, ListFlowable, ListItem, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# Custom colors based on Gasmaster branding
BRAND_NAVY = colors.HexColor('#14283b')
BRAND_ORANGE = colors.HexColor('#f54e00')
BRAND_YELLOW = colors.HexColor('#f7c900')
GRAY_LIGHT = colors.HexColor('#f3f4f6')
GRAY_DARK = colors.HexColor('#4b5563')

def create_header(canvas, doc):
    canvas.saveState()
    
    # Header Background
    canvas.setFillColor(BRAND_NAVY)
    canvas.rect(0, A4[1] - 1.5*inch, A4[0], 1.5*inch, fill=1, stroke=0)
    
    # Add Logo (if exists, fallback to text if not found)
    try:
        logo_path = "/home/daniel/gas-automation/frontend/public/logo_sistema.png"
        canvas.drawImage(logo_path, 0.5*inch, A4[1] - 1.2*inch, width=2.5*inch, height=0.9*inch, preserveAspectRatio=True, mask='auto')
    except Exception:
        canvas.setFont('Helvetica-Bold', 24)
        canvas.setFillColor(colors.white)
        canvas.drawString(0.5*inch, A4[1] - 0.8*inch, "Gasmaster")
        
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(BRAND_YELLOW)
        canvas.drawString(0.5*inch, A4[1] - 1.05*inch, "DISTRIBUIDORA DE GÁS")
        
    # Header Title
    canvas.setFont('Helvetica-Bold', 18)
    canvas.setFillColor(colors.white)
    canvas.drawString(A4[0] - 4*inch, A4[1] - 0.7*inch, "Relatório de Inovação")
    
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(BRAND_YELLOW)
    canvas.drawString(A4[0] - 4*inch, A4[1] - 0.9*inch, "Correções e Melhorias no Admin")
    
    # Add a thin orange accent line under header
    canvas.setStrokeColor(BRAND_ORANGE)
    canvas.setLineWidth(3)
    canvas.line(0, A4[1] - 1.5*inch, A4[0], A4[1] - 1.5*inch)
    
    canvas.restoreState()

def create_footer(canvas, doc):
    canvas.saveState()
    
    # Footer Background
    canvas.setFillColor(GRAY_LIGHT)
    canvas.rect(0, 0, A4[0], 0.6*inch, fill=1, stroke=0)
    
    # Partner Text
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(GRAY_DARK)
    canvas.drawString(0.5*inch, 0.25*inch, "MERCURYGAS - INTEGRATING STANDARD EXCELLENCE")
    
    # Page Number
    canvas.setFont('Helvetica', 9)
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
    
    # Define custom styles
    title_style = ParagraphStyle(
        name='ModernTitle',
        parent=styles['Heading1'],
        fontSize=22,
        spaceAfter=20,
        textColor=BRAND_NAVY,
        fontName='Helvetica-Bold'
    )
    
    h2_style = ParagraphStyle(
        name='ModernH2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=18,
        spaceAfter=12,
        textColor=BRAND_NAVY,
        fontName='Helvetica-Bold',
        borderPadding=(0, 0, 4, 0),
        borderColor=BRAND_ORANGE,
        borderWidth=1,
        borderRadius=0,
    )
    
    h3_style = ParagraphStyle(
        name='ModernH3',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=14,
        spaceAfter=8,
        textColor=BRAND_NAVY,
        fontName='Helvetica-Bold'
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
    
    tip_box_style = ParagraphStyle(
        name='TipBox',
        parent=normal_style,
        backColor=GRAY_LIGHT,
        borderPadding=10,
        borderColor=BRAND_ORANGE,
        borderWidth=1,
        textColor=BRAND_NAVY,
        fontName='Helvetica-Bold'
    )

    story = []
    
    # Intro
    story.append(Paragraph("Avanços Concluídos (05/03/2026)", title_style))
    story.append(Paragraph("Concluímos a implementação das correções dos três bugs centrais e as melhorias estéticas solicitadas. Abaixo está o resumo visual das entregas realizadas ao vivo na infraestrutura.", intro_style))
    story.append(Spacer(1, 0.2 * inch))

    # --- BLOCK 1 ---
    story.append(Paragraph("1. Novo Fluxo de Endereço (Motorista/Robô)", h2_style))
    story.append(Paragraph("O robô agora utiliza um fluxo validado que prioriza a API oficial (ViaCEP) antes de pedir outros detalhes. Isso previne envios de endereços genéricos problemáticos para o App do Motorista.", normal_style))
    
    b1 = [
        ListItem(Paragraph("<b>Novo Framework:</b> Handler exclusivo 'ORDERING_ADDRESS_CEP'.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Inteligência de Busca:</b> Sistema rastreia instantaneamente o CEP preenchendo rua, bairro e cidade magicamente.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Resolução Driver App:</b> Endpoint '/me/deliveries' montado para combinar o log e mitigar 'Endereço não informado'.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b1, bulletType='bullet', bulletFontName='Helvetica'))
    
    # TIP Box
    tip_text = "<b>NOVO FLUXO:</b> 1. Cliente pede gás ➔ 2. Robô: 'Informe seu CEP' ➔ 3. Confirma endereço estruturado."
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(tip_text, tip_box_style))
    story.append(Spacer(1, 0.2 * inch))

    # --- BLOCK 2 ---
    story.append(Paragraph("2. Ajuste do Rastreador de WhatsApp", h2_style))
    story.append(Paragraph("Na etapa do cliente ('Pedido em trânsito'), alteramos a máscara analítica do contato do entregador.", normal_style))
    
    b2 = [
        ListItem(Paragraph("<b>Mascaramento Dinâmico:</b> Se o sistema notar 'joao.driver', o card de contato some do WhatsApp cliente.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Formatação Limpa:</b> Para telefones válidos (DDD), convertemos '55419999...' para a UI humanizada '(41) 9XXXX-XXXX'.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b2, bulletType='bullet', bulletFontName='Helvetica'))
    story.append(Spacer(1, 0.2 * inch))

    # --- BLOCK 3 ---
    story.append(Paragraph("3. Governança e Controle de Administradores", h2_style))
    story.append(Paragraph("Empoderamos os super-admins da Mercury com a habilidade de controlar quem entra nas pontas do sistema.", normal_style))
    
    b3 = [
        ListItem(Paragraph("<b>Hard/Soft Wipe:</b> Botão vermelho para deletar logs e acessos falsos.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Master Keys:</b> Forçar atualização de senha para frentistas e donos a partir do próprio painel com modal-key lock.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b3, bulletType='bullet', bulletFontName='Helvetica'))
    story.append(Spacer(1, 0.4 * inch))

    # --- PAGE BREAK FOR GASMASTER REDESIGN ---
    story.append(PageBreak())
    
    story.append(Paragraph("Identidade Corporativa: Gasmaster Login & Dashboards", title_style))
    story.append(Paragraph("Implementamos não apenas dados soltos, mas uma interface de 'Software Premium' focado em Gás.", intro_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("A. Portal de Entrada (O Novo Split-Screen)", h2_style))
    b4 = [
        ListItem(Paragraph("<b>Ambientação Dinâmica:</b> Fundo unindo o Azul-Navy (#14283b) com o Laranja Vivo vibrante, abolindo as cores básicas.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>Marcas Limpas:</b> Logo Gasmaster injetada na malha visual de forma nativa.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("<b>MercuryGas First:</b> Formulário iluminado ostentando o selo do Integrador (Mercury) em proporção 250% realçada.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b4, bulletType='bullet', bulletFontName='Helvetica'))

    story.append(Paragraph("B. Métricas Globais Ininterruptas", h2_style))
    story.append(Paragraph("Investidores odeiam garimpar dados. Resolvemos esse atrito.", normal_style))
    b5 = [
        ListItem(Paragraph("API segregada '/sidebar-metrics' processando pesagem de Kg & Toneladas dinamicamente.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("Card fixo flutuante em Navbar Lateral evidenciando TONS/mês com traços de crescimento (Verde/Vermelho).", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b5, bulletType='bullet', bulletFontName='Helvetica'))

    story.append(Paragraph("C. GIRO DE ESTOQUE (Overview Físico)", h2_style))
    story.append(Paragraph("Adaptamos o Dashboard comum para um Dashboard de <b>Distribuidora Logística.</b>", normal_style))
    b6 = [
        ListItem(Paragraph("Rankeamento em tempo real do P13 vs P45.", bullet_style), bulletColor=BRAND_ORANGE),
        ListItem(Paragraph("Conversão de Faturamento atrelado à tiragem do tipo de Vasilhame específico.", bullet_style), bulletColor=BRAND_ORANGE)
    ]
    story.append(ListFlowable(b6, bulletType='bullet', bulletFontName='Helvetica'))

    doc.build(story)

if __name__ == "__main__":
    build_graphical_pdf("/app/Relatorio_Visual_GasAutomation.pdf")
