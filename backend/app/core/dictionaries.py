"""
GASMASTER - Dicionario de Sinonimos Completo
Mapeamento extenso de todas as formas que clientes brasileiros
se comunicam via WhatsApp para compra de gas.

Inclui: erros de digitacao, girias, abreviacoes, regionalismos,
linguagem informal e autocorretor do celular.
"""

# ============================================================
# PRODUTOS - Todas as formas de se referir a cada botijao
# ============================================================

PRODUCT_SYNONYMS = {
    "P13": [
        # Codigos oficiais
        "p13", "p 13", "p-13", "p.13",
        # Peso
        "13", "treze", "13kg", "13 kg", "13kilos", "13 kilos",
        "13quilos", "13 quilos", "de 13", "de treze",
        "13kgs", "13 kgs",
        # Tamanho
        "pequeno", "pequeninho", "menor", "normal", "comum",
        "residencial", "de casa", "caseiro", "domestico", "doméstico",
        "o menor", "o pequeno", "o normal", "o comum",
        "botijao pequeno", "botijão pequeno",
        # Opcao numerica (menu)
        "primeiro", "primeira opcao", "primeira opção", "opção 1", "opcao 1",
        # Erros comuns de digitacao
        "p treze", "ptreze", "pe13", "p1e", "p3", "pi3",
        "butijao", "butijão", "botijam", "bujao", "bujão",
        "butijao pequeno", "bujao pequeno",
        "botijao de 13", "botijão de 13",
        "botijao treze", "butijao treze",
        "boitjao", "botijao13", "botijaõ",
        # Girias e coloquial
        "azulzinho", "o azulzinho", "o tradicional", "o padrao", "o padrão",
        "gas de cozinha", "gás de cozinha", "gas normal", "gás normal",
        "o de cozinha", "de cozinha", "o basico", "o básico",
        "o popularr", "o popular",
        # Contexto residencial
        "pra casa", "de casa", "uso domestico", "uso doméstico",
        "residencial", "pro fogao", "pro fogão", "da cozinha",
    ],
    "P20": [
        # Codigos oficiais
        "p20", "p 20", "p-20", "p.20",
        # Peso
        "20", "vinte", "20kg", "20 kg", "20kilos", "20 kilos",
        "20quilos", "20 quilos", "de 20", "de vinte",
        "20kgs", "20 kgs",
        # Tamanho
        "medio", "médio", "intermediario", "intermediário",
        "nem grande nem pequeno", "do meio", "o do meio",
        "o medio", "o médio", "tamanho medio",
        # Uso
        "empilhadeira", "pra empilhadeira", "de empilhadeira",
        "industrial pequeno", "pra empilhadora",
        # Opcao numerica (menu)
        "segundo", "segunda opcao", "segunda opção", "opção 2", "opcao 2",
        # Erros comuns
        "p vinte", "pvinte", "pe20", "p2o", "p 2o",
        "botijao medio", "botijão médio",
        "botijao de 20", "botijão de 20",
        "botijao vinte", "butijao vinte",
        "butijao medio", "bujao medio",
        # Girias
        "o mediano", "o intermediario",
    ],
    "P45": [
        # Codigos oficiais
        "p45", "p 45", "p-45", "p.45",
        # Peso
        "45", "quarenta e cinco", "45kg", "45 kg", "45kilos", "45 kilos",
        "45quilos", "45 quilos", "de 45", "de quarenta e cinco",
        "45kgs", "45 kgs",
        # Tamanho
        "grande", "grandao", "grandão", "maior", "gigante", "enorme",
        "o grande", "o grandao", "o grandão", "o maior",
        "botijao grande", "botijão grande",
        # Uso
        "industrial", "comercial", "de restaurante", "de cozinha industrial",
        "pra empresa", "empresarial", "pro comercio", "pro comércio",
        "pro restaurante", "de padaria", "pra padaria",
        "pra lanchonete", "de lanchonete", "pra pizzaria", "de pizzaria",
        # Opcao numerica (menu)
        "terceiro", "terceira opcao", "terceira opção", "opção 3", "opcao 3",
        "tres", "três",
        # Erros comuns
        "p quarenta e cinco", "pe45", "p4 5", "p 4 5",
        "butijao grande", "bujao grande",
        "botijao de 45", "botijão de 45",
        "botijao quarenta", "butijao quarenta",
        # Girias e coloquial
        "o monstro", "monstrao", "monstrão", "o barril", "barrilzão",
        "o barrilzao", "o bicho", "o grandalhao", "o grandalhão",
        "cilindrao", "cilindrão",
    ],
}

# ============================================================
# QUANTIDADES
# ============================================================

QUANTITY_SYNONYMS = {
    1: [
        "um", "uma", "uno", "só um", "apenas um", "somente um",
        "um só", "um botijão", "um botijao", "single", "um so",
        "apenas 1", "somente 1", "so 1", "so um",
    ],
    2: [
        "dois", "duas", "par", "um par", "dois botijões",
        "dois botijao", "dois botijoes", "2 botijoes",
        "2 botijões", "dois botijão",
    ],
    3: [
        "tres", "três", "trio", "tres botijões",
        "tres botijao", "três botijoes", "3 botijoes",
    ],
    4: [
        "quatro", "quatro botijões", "quatro botijao",
        "4 botijoes",
    ],
    5: [
        "cinco", "cinco botijões", "cinco botijao",
        "5 botijoes",
    ],
    6: [
        "seis", "meia dúzia", "meia duzia", "half dozen",
        "6 botijoes",
    ],
    7: ["sete", "7 botijoes"],
    8: ["oito", "8 botijoes"],
    9: ["nove", "9 botijoes"],
    10: ["dez", "10 botijoes"],
}

# ============================================================
# FORMAS DE PAGAMENTO
# ============================================================

PAYMENT_SYNONYMS = {
    "cash": [
        "dinheiro", "din", "cash", "especie", "espécie",
        "em especie", "em espécie", "na mao", "na mão",
        "em maos", "em mãos", "moeda", "cédula", "cedula",
        "pago em dinheiro", "vou pagar dinheiro",
        "na entrega dinheiro", "dinhero", "dinehiro",
        "dinheiro", "no dinheiro", "com dinheiro",
        "em dinheiro", "pagar dinheiro", "pago dinheiro",
        "a vista", "à vista", "avista",
        "na hora", "quando chegar", "na entrega",
        "pago quando chegar", "pago la", "pago lá",
        "pago na hora", "quando entregar",
    ],
    "credit_card": [
        "cartao", "cartão", "credito", "crédito",
        "cartao de credito", "cartão de crédito",
        "no cartao", "no cartão",
        "passa no cartao", "passa no cartão",
        "cartão credito", "cartao credito",
        "maquininha", "maquina", "máquina",
        "visa", "master", "mastercard", "elo",
        "hipercard", "americanexpress", "amex",
        "na maquininha", "no credito", "no crédito",
        "cartao credito", "cartão crédito",
        "pago no cartao", "pago no cartão",
        "passar no cartao", "passar no cartão",
    ],
    "debit_card": [
        "debito", "débito", "cartao debito", "cartão débito",
        "no debito", "no débito",
        "passa no debito", "passa no débito",
        "cartao de debito", "cartão de débito",
        "no cartao de debito", "no cartão de débito",
        "pago no debito", "pago no débito",
    ],
    "pix": [
        "pix", "px", "pixx", "pixs", "chave pix",
        "pelo pix", "via pix", "manda o pix",
        "qr code", "qrcode", "qr", "código pix",
        "codigo pix", "pago pix", "pago no pix",
        "no pix", "por pix", "transferencia", "transferência",
        "pago via pix", "quero pagar pix",
    ],
}

# ============================================================
# CONFIRMACOES (SIM)
# ============================================================

CONFIRM_SYNONYMS = [
    # Sim direto
    "sim", "simm", "simmm", "s", "ss", "sss", "si", "sii", "siim",
    "simzinho", "simsim", "uhum", "uhumm", "aham", "aha", "ahã",
    "sim sim", "sim por favor", "sim pfv",
    # Correto/Certo
    "certo", "certinho", "certeza", "ctz", "correto", "corretissimo",
    "corretíssimo", "exato", "exatamente", "isso mesmo", "isso",
    "issoai", "isso ai", "isso aí", "isso mesmo", "eh isso",
    "é isso", "é isso mesmo", "é isso ai",
    # Pode/Confirma
    "pode", "pode sim", "pode ser", "podeser", "confirma", "confirm",
    "confirmado", "confirmo", "confirmar", "fechado", "fechou", "fechô",
    "tá certo", "ta certo", "tá bom", "ta bom",
    "tá ok", "ta ok", "combinado", "combinadoo",
    "ok", "okk", "okay", "oks",
    # Positivo informal
    "blz", "beleza", "show", "showzinho", "suave", "de boa",
    "dboa", "tranquilo", "tranks", "trank", "top", "perfeito",
    "bora", "boraa", "vamo", "vamos", "manda", "manda ver",
    "dale", "daleee", "partiu", "vai la", "vai lá",
    "bele", "belê", "show de bola",
    # Confirmacao forte
    "com certeza", "claro", "claroo", "clarooo", "obvio",
    "óbvio", "sem duvida", "sem dúvida", "lógico", "logico",
    "positivo", "afirmativo", "boto fé", "btf", "boto fe",
    "na moral", "valeu", "vlw", "vlww",
    # Girias regionais
    "firmeza", "firme", "firmezaa", "massa", "massaa",
    "daora", "dahora", "irado", "animal",
    "belezinha", "sussa", "sussaa", "na boa", "daboa",
    "tmj", "tamo junto", "bão", "bao", "demais",
    "com fé", "fechadão", "fechadao",
    # Emojis como texto
    "joinha", "like", "positivo",
]

# ============================================================
# NEGACOES (NAO)
# ============================================================

DENY_SYNONYMS = [
    # Nao direto
    "nao", "não", "naoo", "nãoo", "n", "nn", "nnn",
    "nope", "nops", "nem", "nunca", "jamais",
    "de jeito nenhum", "de forma alguma", "nem pensar",
    "nao nao", "não não",
    # Errado/Incorreto
    "errado", "incorreto", "errei", "ta errado", "tá errado",
    "nao é isso", "não é isso", "nao e isso",
    "esse nao", "esse não", "nao esse", "não esse",
    "tá errado isso", "ta errado isso",
    # Cancelar
    "cancela", "cancelar", "cancelo", "cancel", "desisto", "desistir",
    "nao quero mais", "não quero mais",
    "deixa pra la", "deixa pra lá", "esquece",
    "deixa quieto", "para", "parar",
    # Alterar/Trocar
    "quero alterar", "altera", "alterar", "trocar", "troca",
    "mudar", "muda", "outro", "outra", "diferente",
    "quero outro", "quero outra", "quero mudar",
    "nao era esse", "não era esse", "era outro",
    "muda isso", "troca isso",
    # Negacao informal
    "negativo", "que nada", "nananinanao", "nananina",
    "nah", "naah", "capaz", "eita nao", "eita não",
    "xi", "xiii", "puts", "ih", "iih",
    "nada a ver", "nada haver",
]

# ============================================================
# SAUDACOES
# ============================================================

GREETING_SYNONYMS = [
    # Oi/Ola
    "oi", "oii", "oiii", "oie", "oia", "oiie",
    "opa", "opaa", "eai", "e ai", "eae", "e ae",
    "fala", "falaa", "falaaa", "salve", "salvee", "slv", "slve",
    "yo", "eita", "eitaa", "hey", "hei", "hi",
    "ola", "olá", "olaa", "helo", "hello", "alo", "alô",
    # Bom dia
    "bom dia", "bomdia", "bdia", "bom diaaa", "bom diaa", "bd",
    "dia", "born dia", "bon dia", "boom dia", "bão dia", "bao dia",
    "bom diia", "bomm dia",
    # Boa tarde
    "boa tarde", "boatarde", "btarde", "boa tardee", "bt",
    "tarde", "boa tardeee", "bora tarde", "boa tardi",
    "boaa tarde", "boa tardii",
    # Boa noite
    "boa noite", "boanoite", "bnoite", "boa noitee", "bn",
    "noite", "boa noiteee", "bora noite", "boa noiti",
    "boaa noite", "boa noitii",
    # Tudo bem?
    "tudo bem", "tudobem", "td bem", "tdbem", "tudo bom",
    "tudobom", "td bom", "como vai", "cmovai", "cmo vai",
    "como vc ta", "como ta", "como você está",
    # Expressoes informais
    "eaew", "eaee", "coee", "coe", "qual eh", "qualeh",
    "fala tu", "fala ai", "bora", "boraa",
    "cheguei", "to aqui", "vim aqui",
    "e aew", "e aee", "iaee", "iae",
]

# ============================================================
# INTENCAO DE COMPRA
# ============================================================

BUY_KEYWORDS = [
    # Pedidos diretos
    "quero gas", "quero gás", "preciso de gas", "preciso de gás",
    "preciso gas", "preciso gás",
    "quero comprar", "quero pedir", "fazer pedido",
    "manda gas", "manda gás", "manda um gas", "manda um gás",
    "manda um", "manda gaz",
    # Sem gas / acabou
    "sem gas", "sem gás", "to sem gas", "tô sem gás",
    "estou sem gas", "estou sem gás",
    "acabou o gas", "acabou o gás", "gas acabou", "gás acabou",
    "acabou", "acabou meu gas", "acabou meu gás",
    "ficou sem", "fiquei sem",
    # Botijao
    "preciso de um botijao", "preciso de um botijão",
    "quero um botijao", "quero um botijão",
    "quero botijao", "quero botijão",
    "preciso botijao", "preciso botijão",
    # Repetir pedido
    "quero o de sempre", "o de sempre",
    "repete o ultimo", "repete o último",
    "igual da outra vez", "mesmo pedido",
    "o mesmo", "mesmo de sempre", "o mesmo de antes",
    "repete", "repetir pedido", "repete meu pedido",
    "igual ao ultimo", "igual ao último",
    "faz igual", "faz o mesmo",
    # Pedir/Encomendar
    "pedir gas", "pedir gás", "encomenda", "encomendar",
    "quero encomendar", "faz um pedido",
    "fazer um pedido", "novo pedido", "quero fazer pedido",
    # Entregar
    "vcs entregam", "vocês entregam", "entregam gas",
    "entregam gás", "entrega gas", "entrega gás",
    "tem entrega", "faz entrega", "fazem entrega",
    # Comprar
    "comprar gas", "comprar gás", "comprar botijao",
    "comprar botijão", "comprar um gas", "comprar um gás",
    # Precisar urgente
    "preciso urgente", "urgente gas", "urgente gás",
    "gas urgente", "gás urgente",
    # Informacao de preco (pode virar compra)
    "quanto custa", "qual o preco", "qual o preço",
    "quanto ta", "quanto tá", "quanto é", "quanto e",
    "preco do gas", "preço do gás",
    "valor do gas", "valor do gás", "valor",
    "tabela de preco", "tabela de preço",
]

# ============================================================
# RASTREAMENTO / STATUS
# ============================================================

TRACK_KEYWORDS = [
    # Onde esta
    "cade meu pedido", "cadê meu pedido", "kd meu pedido",
    "onde ta", "onde tá", "onde esta", "onde está",
    "cade", "cadê", "kd",
    # Ja saiu
    "ja saiu", "já saiu", "ta vindo", "tá vindo",
    "saiu", "ja ta vindo", "já tá vindo",
    # Tempo
    "quanto tempo", "demora quanto", "vai demorar",
    "quanto falta", "falta quanto",
    "previsão", "previsao", "estimativa",
    "que horas chega", "quando chega",
    # Status
    "qual o status", "status do pedido", "status",
    "como ta o pedido", "como tá o pedido",
    "como ta meu pedido", "como tá meu pedido",
    "situação", "situacao", "andamento",
    "update", "atualização", "atualizacao",
    "meu pedido", "meus pedidos",
    # Historico
    "historico", "histórico", "pedidos anteriores",
    "ultimos pedidos", "últimos pedidos",
    "compras anteriores",
    # Problemas
    "nao chegou", "não chegou", "atrasado",
    "ta atrasado", "tá atrasado", "atrasou",
    "problema com entrega", "deu ruim", "deu problema",
    "sumiu", "perdeu", "nao veio", "não veio",
    "entregador nao chegou", "entregador não chegou",
    "demora demais", "ta demorando", "tá demorando",
]

# ============================================================
# ATENDIMENTO HUMANO
# ============================================================

HUMAN_KEYWORDS = [
    # Atendente
    "atendente", "atendimento", "humano", "pessoa", "gente",
    "falar com alguém", "falar com alguem",
    "quero falar", "preciso falar",
    "chama alguem", "chama alguém",
    # Rejeicao do robo
    "nao quero robo", "não quero robô",
    "quero pessoa real", "atendimento humano",
    "robo burro", "robô burro",
    "nao entende", "não entende", "não entende nada",
    "esse robo", "esse robô", "robo idiota", "robô idiota",
    # Suporte
    "suporte", "ajuda humana",
    "operador", "gerente", "responsavel", "responsável",
    # Reclamacao
    "reclamação", "reclamacao", "reclamar",
    "problema", "muito problema",
    "nao ta funcionando", "não tá funcionando",
    "nao funciona", "não funciona",
    # Horario/Informacao
    "vcs tao aberto", "vocês estão abertos",
    "horário", "horario", "funciona hoje",
    "abre que horas", "que horas abre", "que horas fecha",
    # Contato
    "telefone", "ligar", "liga pra mim", "me liga",
    "numero de telefone", "fone", "tel",
]

# ============================================================
# EMERGENCIA
# ============================================================

EMERGENCY_KEYWORDS = [
    "vazamento", "vazando", "ta vazando", "tá vazando",
    "cheiro de gas", "cheiro de gás",
    "fogo", "pegando fogo", "incendio", "incêndio",
    "perigo", "perigoso", "explosao", "explosão",
    "emergencia", "emergência", "urgencia grave",
    "gas vazando", "gás vazando",
    "cheiro forte", "cheiro estranho de gas",
    "botijao vazando", "botijão vazando",
    "socorro", "bombeiro", "bombeiros",
    "ta pegando fogo", "tá pegando fogo",
]

# ============================================================
# CANCELAMENTO
# ============================================================

CANCEL_KEYWORDS = [
    "cancelar", "cancela", "cancelo", "cancelar pedido",
    "desistir", "desisto", "nao quero mais", "não quero mais",
    "deixa pra la", "deixa pra lá", "esquece", "deixa quieto",
    "parar", "para", "sair", "sai",
    "nao quero", "não quero", "desisti",
    "cancela tudo", "cancela o pedido",
    "nao preciso mais", "não preciso mais",
    "mudei de ideia", "mudei de idéia",
]

# ============================================================
# COMANDOS DE NAVEGACAO
# ============================================================

MENU_KEYWORDS = [
    "menu", "inicio", "início", "home", "começar", "comecar",
    "voltar", "volta", "retornar", "0", "zero",
    "voltar ao inicio", "voltar ao início",
    "menu principal", "tela inicial",
]

HELP_KEYWORDS = [
    "ajuda", "help", "?", "socorro", "me ajuda",
    "como funciona", "como faz",
    "nao entendi", "não entendi",
    "oq eu faco", "o que eu faço",
    "como pedir", "como comprar",
    "como funciona isso", "como que faz",
]

BACK_KEYWORDS = [
    "voltar", "volta", "anterior", "atras", "atrás",
    "errei", "ops", "opa errei", "voltaa",
    "voltar etapa", "etapa anterior",
]

# ============================================================
# ABREVIACOES DO INTERNES BRASILEIRO
# ============================================================

ABBREVIATIONS = {
    # Pronomes
    "vc": "voce",
    "vcs": "voces",
    "ce": "voce",
    "cê": "voce",
    "tu": "voce",
    # Conjuncoes/Advérbios
    "tb": "tambem",
    "tbm": "tambem",
    "tmb": "tambem",
    "pq": "porque",
    "pqe": "porque",
    "pqi": "porque",
    "oq": "o que",
    "oque": "o que",
    "oqi": "o que",
    "qd": "quando",
    "qdo": "quando",
    "qnd": "quando",
    "qndo": "quando",
    "hj": "hoje",
    "hje": "hoje",
    # Intensidade
    "mt": "muito",
    "mto": "muito",
    "mta": "muita",
    "d+": "demais",
    "d ++": "demais",
    # Cordialidade
    "pfv": "por favor",
    "pf": "por favor",
    "pfvr": "por favor",
    "plz": "por favor",
    "obg": "obrigado",
    "obgd": "obrigado",
    "obgda": "obrigada",
    "brigado": "obrigado",
    "brigada": "obrigada",
    # Despedida
    "flw": "falou",
    "flws": "falou",
    "fw": "falou",
    "vlw": "valeu",
    "vlws": "valeu",
    "vlww": "valeu",
    # Localizacao
    "kd": "cade",
    "kade": "cade",
    "aki": "aqui",
    "aq": "aqui",
    "ai": "ai",
    # Tempo
    "agr": "agora",
    "ag": "agora",
    "dps": "depois",
    "dpois": "depois",
    "dnv": "de novo",
    "denovo": "de novo",
    # Comunicacao
    "msg": "mensagem",
    "sdds": "saudades",
    "sdd": "saudades",
    "ctz": "certeza",
    "vdd": "verdade",
    "vrd": "verdade",
    # Companhia
    "cmg": "comigo",
    "cmigo": "comigo",
    "ctg": "contigo",
    "cntg": "contigo",
    # Polidez
    "dnd": "de nada",
    "denada": "de nada",
    "abs": "abracos",
    "abrs": "abracos",
    "bjs": "beijos",
    "bj": "beijo",
    "bjss": "beijos",
    # Preposicoes e artigos
    "cm": "com",
    "q": "que",
    "ki": "que",
    "ke": "que",
    "p/": "para",
    "pra": "para",
    "pr": "para",
    # Verbos
    "n": "nao",
    "naum": "nao",
    "num": "nao",
    "ta": "esta",
    "tá": "esta",
    "to": "estou",
    "tô": "estou",
    "tou": "estou",
    "eh": "e",
    "é": "e",
    # Identidade
    "msm": "mesmo",
    "msmo": "mesmo",
    "qq": "qualquer",
    "qlqr": "qualquer",
    "qm": "quem",
    "qem": "quem",
    # Confirmacao
    "ss": "sim",
    "sss": "sim",
    "blz": "beleza",
    "bls": "beleza",
    "bele": "beleza",
    "belê": "beleza",
    # Expressoes
    "slk": "se loko",
    "slc": "se loko",
    "sqn": "so que nao",
}

# ============================================================
# ERROS ORTOGRAFICOS COMUNS
# (Mapeamento de erros frequentes -> forma correta)
# ============================================================

COMMON_TYPOS = {
    # Gas
    "gaz": "gas",
    "gaas": "gas",
    "gass": "gas",
    "gás": "gas",
    # Botijao
    "botijao": "botijao",
    "butijão": "botijao",
    "butijao": "botijao",
    "bujão": "botijao",
    "bujao": "botijao",
    "botijam": "botijao",
    "boitjao": "botijao",
    "botijaõ": "botijao",
    # Endereco
    "endereco": "endereco",
    "endreco": "endereco",
    "endresso": "endereco",
    "endressu": "endereco",
    # Entrega
    "emtrega": "entrega",
    "entrga": "entrega",
    "entregaa": "entrega",
    "entregua": "entrega",
    # Dinheiro
    "dinehiro": "dinheiro",
    "dinhero": "dinheiro",
    "dinheiroo": "dinheiro",
    # Cartao
    "cartam": "cartao",
    "caratão": "cartao",
    "cartaõ": "cartao",
    # Pedido
    "prdido": "pedido",
    "pedidoo": "pedido",
    "pedidu": "pedido",
    "pedifo": "pedido",
    # Voce
    "voçe": "voce",
    "vocé": "voce",
    # Quero
    "kero": "quero",
    "queiro": "quero",
    "queroo": "quero",
    "qro": "quero",
    "qero": "quero",
    # Troco
    "troko": "troco",
    "trocoo": "troco",
    "trco": "troco",
    "torco": "troco",
    # Preco
    "preco": "preco",
    "presu": "preco",
    "presso": "preco",
    # Obrigado
    "obrigadu": "obrigado",
    "obrgado": "obrigado",
    "obrigadoo": "obrigado",
    # Sim
    "sin": "sim",
    "simm": "sim",
    "simmm": "sim",
    "sii": "sim",
    # Nao
    "naum": "nao",
    "nan": "nao",
    "naõ": "nao",
}

# ============================================================
# EXPRESSOES DE TEMPO E URGENCIA
# ============================================================

URGENCY_KEYWORDS = {
    "immediate": [
        "agora", "urgente", "urgência", "urgencia",
        "emergencia", "emergência",
        "pra já", "pra ja", "imediato",
        "rapido", "rápido", "correndo", "voando",
        "logo", "asap", "o mais rapido", "o mais rápido",
        "o mais rapido possivel", "o mais rápido possível",
        "já", "ja", "agora já", "agora ja",
        "preciso agora", "preciso urgente",
        "nao pode demorar", "não pode demorar",
    ],
    "today": [
        "hoje", "hj", "ainda hoje", "no dia de hoje",
        "durante o dia", "ate mais tarde", "até mais tarde",
        "antes de fechar", "antes de acabar o dia",
        "pro dia de hoje", "durante a tarde",
    ],
    "specific": [
        "de manha", "de manhã", "pela manha", "pela manhã",
        "de tarde", "a tarde", "à tarde", "pela tarde",
        "de noite", "a noite", "à noite", "pela noite",
        "depois do almoco", "depois do almoço",
        "fim de tarde", "começo da noite", "comeco da noite",
        "meio dia", "ao meio dia",
        "de manha cedo", "de manhã cedo",
    ],
    "flexible": [
        "quando puder", "qnd puder", "sem pressa",
        "tranquilo", "qualquer hora", "qq hora",
        "tanto faz", "pode ser amanha", "pode ser amanhã",
        "depois", "sem urgencia", "sem urgência",
        "quando der", "quando tiver", "nao tem pressa",
        "não tem pressa", "fica a vontade",
    ],
}

# ============================================================
# TROCO - Expressoes para pedir troco
# ============================================================

CHANGE_KEYWORDS = [
    "troco", "troco pra", "troco para", "troco de",
    "preciso de troco", "tem troco", "leva troco",
    "manda troco", "troco p/",
    "vai precisar de troco", "preciso troco",
    "traz troco", "trazer troco",
]

# ============================================================
# "O DE SEMPRE" - Expressoes para repetir pedido
# ============================================================

REPEAT_ORDER_KEYWORDS = [
    "o de sempre", "de sempre", "o mesmo",
    "mesmo de sempre", "o mesmo de antes",
    "repete", "repetir", "repete o ultimo", "repete o último",
    "igual da outra vez", "igual ao ultimo", "igual ao último",
    "mesmo pedido", "pedido igual",
    "faz igual", "faz o mesmo", "o habitual",
    "como da ultima vez", "como da última vez",
    "o que eu sempre peço", "o que sempre peco",
    "o usual", "o costumeiro",
]

# ============================================================
# EXPRESSOES PARA ALTERAR PEDIDO
# ============================================================

EDIT_KEYWORDS = [
    "alterar", "altera", "mudar", "muda", "trocar", "troca",
    "quero alterar", "quero mudar", "quero trocar",
    "alterar pedido", "mudar pedido", "trocar pedido",
    "editar", "edita", "edit", "corrigir", "corrige",
    "modificar", "modifica",
]

EDIT_PRODUCT_KEYWORDS = [
    "produto", "botijao", "botijão", "tipo",
    "trocar produto", "mudar produto", "outro produto",
    "outro botijao", "outro botijão",
    "quero outro tipo", "tipo diferente",
]

EDIT_QUANTITY_KEYWORDS = [
    "quantidade", "qtd", "qtde",
    "mudar quantidade", "trocar quantidade",
    "mais", "menos", "aumentar", "diminuir",
    "quero mais", "quero menos",
]

EDIT_ADDRESS_KEYWORDS = [
    "endereco", "endereço", "local", "endresso",
    "mudar endereco", "mudar endereço",
    "trocar endereco", "trocar endereço",
    "outro endereco", "outro endereço",
    "outro local", "lugar diferente",
    "entregar em outro lugar",
]

EDIT_PAYMENT_KEYWORDS = [
    "pagamento", "forma de pagamento", "pagar",
    "mudar pagamento", "trocar pagamento",
    "outra forma", "outro pagamento",
    "pagar diferente", "mudar forma de pagar",
]


# ============================================================
# FAQ / PERGUNTAS FORA DE CONTEXTO
# ============================================================

FAQ_KEYWORDS = {
    "horario": [
        "horario", "hora", "abre", "fecha", "funcionamento",
        "aberto", "fechado", "expediente", "que horas",
        "horario de funcionamento", "abre que horas",
        "fecha que horas", "ate que horas",
    ],
    "entrega": [
        "demora", "quanto tempo", "previsao", "prazo",
        "tempo de entrega", "demora quanto", "quanto demora",
        "chega em quanto tempo", "prazo de entrega",
    ],
    "area": [
        "regiao", "bairro que atende", "atende", "entregam",
        "cobertura", "entrega no", "entrega em", "atende no",
        "atende em", "area de entrega", "area de cobertura",
        "quais bairros", "onde entregam", "onde atende",
    ],
    "pagamento_info": [
        "aceita", "forma de pagamento", "como pagar",
        "aceita cartao", "aceita pix", "aceita dinheiro",
        "quais formas", "formas de pagamento",
        "como posso pagar", "meios de pagamento",
    ],
    "preco": [
        "preco", "valor", "quanto custa", "tabela",
        "quanto ta", "quanto e", "tabela de precos",
        "valores", "quanto sai",
    ],
}

FAQ_RESPONSES = {
    "horario": "Funcionamos de segunda a sabado, das 8h as 18h.",
    "entrega": "O prazo de entrega e de aproximadamente {tempo} minutos apos a confirmacao do pedido.",
    "area": "Atendemos os bairros: {bairros}.",
    "pagamento_info": "Aceitamos: Dinheiro, Cartao (credito/debito) e PIX.",
    "preco": (
        "Nossos produtos:\n"
        "- *P13* (13kg) - botijao residencial\n"
        "- *P20* (20kg) - botijao comercial\n"
        "- *P45* (45kg) - botijao industrial\n\n"
        "Para valores atualizados, digite *comprar*."
    ),
}
