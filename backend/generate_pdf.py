from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

def create_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=14,
        textColor=HexColor('#14283b')
    )
    
    h2_style = ParagraphStyle(
        name='CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=10,
        textColor=HexColor('#f54e00')
    )

    h3_style = ParagraphStyle(
        name='CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=8,
        textColor=HexColor('#14283b')
    )

    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.spaceAfter = 8

    bullet_style = styles['Normal']
    bullet_style.fontSize = 11
    bullet_style.spaceAfter = 4

    story = []

    # Title
    story.append(Paragraph("Relatório de Implementação: Correções e Melhorias no Admin/Motorista", title_style))
    story.append(Paragraph("Concluímos a implementação das correções dos três bugs e melhorias solicitados. Abaixo está o resumo das alterações realizadas:", normal_style))
    story.append(Spacer(1, 0.2 * inch))

    # Section 1
    story.append(Paragraph("1. Novo Fluxo de Endereço (Prioridade CEP)", h2_style))
    story.append(Paragraph("O robô agora utiliza um fluxo validado de endereço que prioriza a busca pelo CEP antes de pedir outros detalhes. Isso previne o envio de endereços genéricos (como \"Curitiba\", que o antigo Nominatim retornava) e garante uma formatação precisa para o App do Entregador.", normal_style))
    
    bullets1 = [
        ListItem(Paragraph("<b>Implementação do Novo Estado:</b> Criado o estado ORDERING_ADDRESS_CEP e seu respectivo handler OrderingAddressCEPHandler.", bullet_style)),
        ListItem(Paragraph("<b>Validação ViaCEP:</b> O sistema agora consulta a API do ViaCEP assim que o cliente informa o CEP para buscar rua, bairro e cidade.", bullet_style)),
        ListItem(Paragraph("<b>Confirmação e Coleta de Número:</b> Após encontrar o CEP, o robô confirma a rua e pergunta apenas o número e complemento.", bullet_style)),
        ListItem(Paragraph("<b>Melhoria na Exibição do Driver App:</b> O endpoint de listagem de entregas (/me/deliveries) foi reforçado para mesclar corretamente o endereço estruturado no campo delivery_address_str, resolvendo o problema de \"Endereço não informado\" no app.", bullet_style))
    ]
    story.append(ListFlowable(bullets1, bulletType='bullet'))
    
    story.append(Paragraph("<i>DICA - Fluxo atualizado do Atendimento:</i>", normal_style))
    flow_bullets = [
        ListItem(Paragraph("1. Cliente solicita botijão (ou garrafão).", bullet_style)),
        ListItem(Paragraph("2. Robô pede o CEP: <i>\"Para calcularmos o tempo de entrega, por favor me informe o seu CEP (apenas números).\"</i>", bullet_style)),
        ListItem(Paragraph("3. Se encontrado, robô confirma e pede o número.", bullet_style)),
        ListItem(Paragraph("4. Endereço é salvo estruturado (rua, número, bairro, CEP).", bullet_style))
    ]
    story.append(ListFlowable(flow_bullets, bulletType='bullet', start='1'))
    story.append(Spacer(1, 0.2 * inch))

    # Section 2
    story.append(Paragraph("2. Correção do Número de Telefone do Motorista", h2_style))
    story.append(Paragraph("Na mensagem enviada via WhatsApp ao cliente quando o pedido entra \"Em trânsito\", o sistema exibia erroneamente o login do motorista (ex: joao.driver) em vez do telefone.", normal_style))
    
    bullets2 = [
        ListItem(Paragraph("<b>Função de Formatação:</b> Foi criada uma função _format_phone_display que identifica se o campo de telefone do motorista parece ser um número brasileiro válido (ex: 5541999999999).", bullet_style)),
        ListItem(Paragraph("<b>Comportamento Inteligente:</b> Se for um número válido, a mensagem exibe no formato amigável: (41) 9XXXX-XXXX. Caso contrário (se for usado um login de e-mail/username), o campo de telefone é omitido da mensagem para evitar confundir o cliente.", bullet_style))
    ]
    story.append(ListFlowable(bullets2, bulletType='bullet'))
    story.append(Spacer(1, 0.2 * inch))

    # Section 3
    story.append(Paragraph("3. Melhorias no Dashboard de Usuários do Admin", h2_style))
    story.append(Paragraph("Atualizamos o painel administrativo para fornecer muito mais controle ao gerenciador do sistema sobre os usuários/operadores da plataforma.", normal_style))
    
    bullets3 = [
        ListItem(Paragraph("<b>Exclusão de Usuários:</b> Adicionado um recurso de \"Soft Delete\" seguro na API e UI. Admins agora podem desativar rapidamente um operador com confirmação de exclusão (com botão no frontend e endpoint DELETE /admin/users/{user_id}).", bullet_style)),
        ListItem(Paragraph("<b>Definição Direta de Senha:</b> Criado um modal no frontend com um ícone de cadeado que acessa o novo endpoint POST /admin/users/{user_id}/set-password. Isso permite que o admin defina senhas específicas para os usuários e indique se eles precisam trocá-la no primeiro acesso.", bullet_style)),
        ListItem(Paragraph("<b>Melhorias de UI:</b> Melhoria geral no visual da tabela (inclusão de ícones na coluna de ações) e na criação de usuários (permitindo especificar o username exato junto com uma senha customizada já na criação).", bullet_style))
    ]
    story.append(ListFlowable(bullets3, bulletType='bullet'))
    
    story.append(Paragraph("<i>NOTA: Você já pode acessar a página de Admin de usuários no frontend e testar a rotina de alterar senhas personalizadas ou apagar contas de testes que não são mais úteis.</i>", normal_style))
    story.append(Spacer(1, 0.2 * inch))

    # Manual Verifications
    story.append(Paragraph("Verificação Manual", h2_style))
    story.append(Paragraph("Como estas correções envolvem APIs de Terceiros e frontends, recomenda-se realizar um teste prático de ponta a ponta:", normal_style))
    manual_bullets = [
        ListItem(Paragraph("<b>Robô:</b> Inicie um novo pedido e confirme que ele solicita seu CEP em vez do antigo \"Qual o seu endereço?\".", bullet_style)),
        ListItem(Paragraph("<b>Dashboard Admin:</b> Acesse como admin local para excluir um usuário teste ou trocar a senha de um.", bullet_style))
    ]
    story.append(ListFlowable(manual_bullets, bulletType='bullet', start='1'))
    story.append(Spacer(1, 0.3 * inch))

    # Implementations Gasmaster
    story.append(Paragraph("Implementação Novo Portal: Gasmaster & Métricas Executivas", title_style))
    story.append(Paragraph("Além das correções descritas acima, também completamos a revitalização visual e tática focando na persona do Dono/Logístico.", normal_style))
    
    # 1. Novo Design 
    story.append(Paragraph("1. Novo Design da Tela de Login (Identidade Gasmaster)", h3_style))
    bullets_gm1 = [
        ListItem(Paragraph("Refizemos por completo o arquivo Login.jsx criando um layout sofisticado de tela dividida (split-screen).", bullet_style)),
        ListItem(Paragraph("O lado esquerdo apresenta uma mensagem corporativa moderna interagindo com as cores originais da Gasmaster (fundo azul-escuro institucional em degradê vibrante com laranja estilo loveable). Foi adicionada a imagem completa da marca Gasmaster.", bullet_style)),
        ListItem(Paragraph("Os textos de base foram atualizados ressaltando a parceria <i>\"Integrando o padrão de qualidade Gasmaster com a automação em tempo real do sistema MercuryGas\"</i> junto a tag <b>POWERED BY MAXWARE</b> na base.", bullet_style)),
        ListItem(Paragraph("O lado direito abriga o formulário 'clean' de login contendo o logo oficial (MercuryGas) no topo sensivelmente ampliado (escala visual superior a 200%) para reforço puro e impacto da marca do software base.", bullet_style))
    ]
    story.append(ListFlowable(bullets_gm1, bulletType='bullet'))

    # 2. Sidebar Volume
    story.append(Paragraph("2. Controle de Volume Global (Sidebar)", h3_style))
    bullets_gm2 = [
        ListItem(Paragraph("Construímos a nova API GET /owner/sidebar-metrics responsável por escanear o banco de dados e somar assertivamente o total de Quilogramas e Toneladas de gás vendidos pelo Delivery no mês.", bullet_style)),
        ListItem(Paragraph("No Frontend, criamos o componente SidebarVolumeCard e o \"injetamos\" nativamente na barra lateral do Dashboard. O Investidor/Dono agora tem acesso ininterrupto à volumetria de gás movimentada em qualquer tela do seu painel.", bullet_style))
    ]
    story.append(ListFlowable(bullets_gm2, bulletType='bullet'))

    # 3. Visão Dashboard
    story.append(Paragraph("3. Repaginação do Dashboard (Giro Físico de Botijões)", h3_style))
    bullets_gm3 = [
        ListItem(Paragraph("A visão executiva do dono (DashboardOverview.jsx) foi estruturada para incorporar ativamente a movimentação de produtos.", bullet_style)),
        ListItem(Paragraph("Desenhamos uma seção nova <b>Giro de Estoque Físico</b> logo acima de \"Operação\". Nela, os dados de movimentação são classificados mostrando os botijões \"campeões de vendas\" em unidade e respectivo retorno financeiro (Ex: P13, P45 e P20).", bullet_style))
    ]
    story.append(ListFlowable(bullets_gm3, bulletType='bullet'))

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("<i>NOTA: Acesse /login para se deslumbrar com a nova tela de entrada. Em seguida, acesse como dono@... para avaliar a usabilidade e exatidão das métricas KG/Ton no canto inferior esquerdo e o rankeamento ágil de botijões!</i>", normal_style))

    doc.build(story)

if __name__ == "__main__":
    create_pdf("/app/Relatorio_Implementacoes_GasAutomation.pdf")
