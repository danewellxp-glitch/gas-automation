# NF-e (SEFAZ / Unimake Cloud) — Gap Audit

- **Data:** 2026-05-02
- **Autor:** Senior Backend Engineer
- **Issue:** [MAX-23](/MAX/issues/MAX-23) — reporta para [MAX-11](/MAX/issues/MAX-11) (Risco R-05)
- **Escopo:** `backend/app/services/financeiro/nfe_service.py` + dependências diretas
- **Recomendação resumo:** **Sim, contratar consultoria fiscal antes do go-live em produção.** A integração atual cobre uma fração mínima do contrato fiscal exigido para distribuidores de GLP no Brasil; ir para `UNIMAKE_AMBIENTE=1` (produção) no estado atual gera risco regulatório real (multa, suspensão de IE, glosa de crédito ICMS-ST do GLP).

## 1. Sumário executivo

Hoje o serviço **gera um XML de NF-e/NFC-e mod. 55/65 simplificado**, envia para a API HTTP da Unimake Cloud em uma única tentativa, persiste o resultado em `notas_fiscais` e tenta reenviar o DANFE por WhatsApp. Faltam praticamente todos os controles operacionais que a SEFAZ exige no fluxo regular de um contribuinte autorizado:

- Numeração sequencial gerenciada pela aplicação (hoje `nNF=0` hard-coded — XML inválido).
- Cálculo da chave de acesso (44 dígitos) — recebida da Unimake mas não verificada.
- Carta de Correção Eletrônica (CC-e), Inutilização de numeração, Manifestação do Destinatário.
- Modo de **Contingência** (SVC-RS / SVC-AN / FS-DA) quando o ambiente autorizador da SEFAZ-PR cai.
- Tributação correta para GLP (CST 060 — ICMS-ST por substituição tributária; o código atual hard-codeia `CSOSN 400` Simples Nacional sem ICMS, o que **não vale para GLP** mesmo no Simples — GLP tem regime especial monofásico de PIS/COFINS e ICMS-ST recolhido pela refinaria/distribuidora primária).
- Retry/idempotência em chamadas à Unimake, gestão de timeouts, observabilidade (correlação por chave/recibo).
- Conhecimento de Transporte Eletrônico (CT-e) e MDF-e — obrigatórios para distribuidoras que operam transporte próprio entre depósitos.
- Gerenciamento operacional do certificado A1/A3 (renovação, expiração, alerta) — hoje totalmente delegado à Unimake; sem visibilidade interna.

Este relatório lista cada gap com severidade, esforço estimado e responsável recomendado. **Recomendamos travar `UNIMAKE_AMBIENTE=2` (homologação) por feature flag até os P0/P1 estarem fechados** e contratar consultoria fiscal externa para validar o XML antes do primeiro go-live.

## 2. Inventário do estado atual

### 2.1 Código

| Arquivo | LOC | Responsabilidade |
|---|---|---|
| `backend/app/services/financeiro/nfe_service.py` | 387 | `NFeService` — gerar XML, enviar para Unimake, cancelar, enviar DANFE WhatsApp |
| `backend/app/models/financeiro/nota_fiscal.py` | 71 | Modelo `NotaFiscal` (tabela `notas_fiscais`) |
| `backend/app/api/financeiro.py:1255-1310` | ~55 | Endpoints `POST /nfe/emitir`, `POST /nfe/{id}/cancelar`, `POST /nfe/{id}/reenviar-whatsapp` |
| `backend/app/services/financeiro/financial_hooks.py:224-245` | ~22 | `on_order_delivered_nfe` — emissão automática após entrega |

### 2.2 Tipos de documento suportados (parcialmente)

| Doc | Modelo | Status no código |
|---|---|---|
| NFC-e (consumidor final) | 65 | Estrutura mínima gerada para CPF/anônimo (`tipo="65"`) |
| NF-e venda | 55 | Estrutura mínima gerada para CNPJ (`tipo="55"`) |
| CT-e (transporte) | 57 | ❌ Não implementado |
| MDF-e (manifesto) | 58 | ❌ Não implementado |
| NFC-e modo contingência off-line (FS-DA) | 65 | ❌ Não implementado |
| NF-e em contingência (SVC-RS/SVC-AN) | 55 | ❌ Não implementado |
| Carta de Correção (CC-e) | n/a | ❌ Não implementado |
| Inutilização de numeração | n/a | ❌ Não implementado |
| Manifestação do destinatário | n/a | ❌ Não implementado (irrelevante p/ emissor; relevante se a empresa receber NF-e de fornecedores) |

### 2.3 Ambientes / configuração

Vars em `.env.example` (todas vazias por padrão):

```
UNIMAKE_API_TOKEN=
UNIMAKE_AMBIENTE=2          # 1=Produção, 2=Homologação
UNIMAKE_API_URL=https://api.unimake.com.br
NFE_CNPJ=
NFE_RAZAO_SOCIAL=
NFE_NOME_FANTASIA=
NFE_LOGRADOURO=
NFE_NUMERO=
NFE_BAIRRO=
NFE_MUNICIPIO=Curitiba
NFE_UF=PR
NFE_CEP=
NFE_TELEFONE=
NFE_IE=
NFE_REGIME_TRIBUTARIO=1     # 1=Simples Nacional, 2=Normal, 3=Lucro Real
NFE_NCM_GAS=27111900
NFE_NCM_AGUA=22011000
NFE_CFOP_VENDA=5102
NFE_ALIQ_ICMS=0.0
NFE_ALIQ_PIS=0.0
NFE_ALIQ_COFINS=0.0
NFE_CSOSN=400
```

Não há separação por **filial / IE / série** — assume um único emissor (uma única loja). Distribuidoras de GLP costumam ter mais de uma IE (matriz + depósitos). Sem multi-IE não dá para escalar para o segundo cliente.

### 2.4 Retry / erro / observabilidade

Em `nfe_service.py:215-246` (`enviar_para_sefaz`):

```python
async with httpx.AsyncClient(timeout=30) as client:
    resp = await client.post(...)
data = resp.json()
if resp.status_code == 200 and data.get("status") == "autorizada":
    nf.status = "autorizada"; ...
else:
    nf.status = "rejeitada"; nf.motivo_rejeicao = data.get("motivo", str(data))
```

- **Sem retry**, sem exponential backoff, sem `tenacity`/`backoff` (`rg "retry|tenacity|backoff" backend/app/services/financeiro` retorna 0 hits).
- **Sem distinção** entre erros transitórios (timeout / 5xx Unimake / SEFAZ off-line) e erros definitivos (rejeição por validação fiscal / chave duplicada). Tudo vira `"rejeitada"` ou `"erro_emissao"`.
- **Sem idempotency-key** na chamada à Unimake. Se a request der timeout depois de o pedido chegar à SEFAZ, um retry naive emite NF duplicada.
- **Sem trace_id / correlation-id** propagado nos logs do `nfe_service`. Logs são `logger.error(f"Erro ao enviar NF-e para SEFAZ: {e}")` sem contexto.
- **`emitir_nfe_pedido` engole exceções da SEFAZ** (linhas 294-303) e ainda assim devolve a `NotaFiscal` com status `enviada` ou `rascunho` — o caller HTTP responde `201` mesmo com NF não autorizada.

### 2.5 Assinatura digital

O código nunca toca em XMLDSig: a assinatura é responsabilidade da **Unimake Cloud** (delega 100%). Implicações:

- Certificado digital fica em posse de terceiro (Unimake hospeda A1 ou A3 via HSM cloud).
- **Não temos cópia local do certificado** nem visibilidade de validade/expiração.
- **Não há alerta** se o certificado vence em <30 dias.
- Em caso de rescisão com a Unimake, perdemos capacidade de emitir até obter novo provider — sem plano B.

### 2.6 Banco de dados (`notas_fiscais`)

Existe (`nota_fiscal.py:14-71`), com índices em `pedido_id`, `customer_id`, `status`, `numero`, `chave_acesso`. Pontos:

- **`numero` é `Optional[Integer]`** — implementação atual deixa SEFAZ/Unimake atribuir e devolver. Isso **viola o contrato de numeração da SEFAZ**: a numeração sequencial é responsabilidade do *contribuinte emissor*, não do autorizador. Em uma queda da Unimake, perdemos o controle do próximo `nNF`.
- **Sem coluna `protocolo_autorizacao`** (cProt) — sem ele, a NF-e não é juridicamente válida (é o número que prova que a SEFAZ recebeu).
- **Sem coluna `recibo`** (nRec) para pollings de status assíncrono.
- **Sem `data_autorizacao` (`dhRecbto`)** distinta de `emitida_at`.
- **Sem coluna `serie` configurável por emissão** (hard-coded "001" no model, "1" no XML — divergência).
- **Sem campo para CC-e / cancelamento** (apenas `cancelamento_protocolo` que nunca é gravado — `cancelar_nfe` em `nfe_service.py:369-383` muda status mas **não chama a Unimake**).

### 2.7 Testes

`rg "test_nfe|test.*nota_fiscal" backend/tests` retorna **zero arquivos**. Nenhum teste unitário ou de integração para o fluxo NF-e — nem com mock da Unimake, nem com sandbox da SEFAZ. R-05 não pode ser desbloqueado para produção sem cobertura mínima de happy-path + erro.

## 3. Comparativo — exigências SEFAZ para distribuidor de GLP

Resumo da Receita Federal / SEFAZ-PR para o segmento (referência: NT 2024.001, Manual de Orientação do Contribuinte v7.00, Convênio ICMS 110/07 + Convênio 18/22 sobre combustíveis, RICMS-PR Anexo IX):

| Exigência | Fonte | Coberto hoje? |
|---|---|---|
| NFC-e mod 65 para venda PF a consumidor final | MOC v7.00 | ⚠️ Parcial (XML inválido — `nNF=0`) |
| NF-e mod 55 para venda PJ / atacado | MOC v7.00 | ⚠️ Parcial (mesma limitação) |
| Numeração sequencial gerida pelo emissor, sem buracos | MOC § 4.1 | ❌ |
| Inutilização para "buracos" de numeração | MOC § 7 | ❌ |
| Carta de Correção (CC-e) — corrigir até 30 dias após autorização | NT 2011.004 | ❌ |
| Cancelamento via Evento (24h regra geral, 168h NFC-e PR) | NT 2012.003 | ❌ (apenas marca status no DB; não chama Unimake/SEFAZ) |
| Modo de Contingência SVC-RS / SVC-AN / FS-DA | NT 2013.007 | ❌ |
| ICMS-ST GLP — CST 060 / CSOSN 500 quando combustível já tributado por ST a montante | Conv. ICMS 110/07; RICMS-PR Anexo IX Art. 491+ | ❌ (código usa CSOSN 400 — "Não Tributada pelo Simples", o que está fiscalmente incorreto para GLP) |
| Tributação monofásica PIS/COFINS para GLP — alíquotas zero ou específicas | Lei 9.718/98 art. 4º; Lei 10.336/01; Lei 11.196/05 | ❌ (cobra `nfe_aliq_pis * total / 100`, default 0% — coincidentemente "não erra" mas só por que default zerado; conta errada se alguém setar alíquota; e falta CST PIS/COFINS 04 ou 06 — está enviando CST `01`) |
| CT-e para transporte do gás entre depósitos / refinaria | Ajuste SINIEF 09/07 | ❌ |
| MDF-e para deslocamentos com mais de 1 NF / interestaduais | Ajuste SINIEF 21/10 | ❌ |
| Backup local / contingência se Unimake cair | LGPD + boa prática contábil | ❌ |
| Guarda do XML autorizado por 5 anos | Lei 8.218/91 art. 11 | ⚠️ XML está em coluna TEXT no Postgres; sem política de retenção/backup separada |
| Reciclagem de vasilhame → operação não tributada (CFOP 5949 / 5916) | RICMS-PR | ❌ (todas as operações usam `nfe_cfop_venda`, default `5102`) |
| Comodato de vasilhame (P13/P20/P45) | Conv. ICMS 88/91 | ❌ não modelado |

## 4. Lista de gaps com severidade e esforço

Severidade: **P0** = bloqueia produção, **P1** = bloqueia produção em > 1 distribuidor / risco de multa, **P2** = melhoria operacional, **P3** = nice-to-have.

| ID | Gap | Sev | Esforço (dev) | Owner | Observação |
|---|---|---|---|---|---|
| NFE-01 | `nNF=0` hard-coded em `gerar_xml_nfe` (linha 126) — XML inválido | P0 | 1d | Senior Backend | Implementar gerador sequencial por (CNPJ, série, modelo) com lock no Postgres |
| NFE-02 | CSOSN 400 hard-coded para GLP — fiscalmente incorreto | P0 | 2d (com consultor fiscal) | Senior Backend + consultor | GLP tem ICMS-ST monofásico + PIS/COFINS específicos |
| NFE-03 | `cancelar_nfe` não chama Unimake/SEFAZ (apenas muda DB) | P0 | 1d | Senior Backend | Endpoint Unimake p/ evento de cancelamento |
| NFE-04 | Sem cobertura de teste (unit + sandbox SEFAZ) | P0 | 3d | Senior Backend | Mock Unimake + smoke contra ambiente 2 |
| NFE-05 | `enviar_para_sefaz` engole exceções e devolve 201 mesmo em falha | P0 | 0.5d | Senior Backend | Propagar status para o endpoint HTTP |
| NFE-06 | Sem retry / idempotency-key — risco de NF duplicada em timeout | P1 | 1.5d | Senior Backend | `tenacity` + idempotency_key=`pedido_id` |
| NFE-07 | Modo contingência (SVC-RS/SVC-AN/FS-DA) ausente | P1 | 3d | Senior Backend + consultor | Quando SEFAZ-PR cai > X min, cair para SVC-RS automaticamente |
| NFE-08 | Sem alerta de validade de certificado A1 (visibilidade de Unimake) | P1 | 1d | Senior Backend | Endpoint Unimake `/certificado/status` + alerta < 30d |
| NFE-09 | Sem CC-e (Carta de Correção) | P1 | 1.5d | Senior Backend | Evento `cce` na Unimake; UI no financeiro |
| NFE-10 | Sem Inutilização de numeração | P1 | 1d | Senior Backend | Necessário quando ID-02 implementar gestão local de `nNF` |
| NFE-11 | Sem `protocolo_autorizacao`, `recibo`, `data_autorizacao` no model | P1 | 0.5d (migration) | Senior Backend | Migration Alembic + backfill |
| NFE-12 | Multi-IE / multi-emissor não suportado | P1 | 3d | Senior Backend | Configuração por `tenant`/`filial` em vez de globals |
| NFE-13 | `serie` divergente entre model ("001") e XML ("1") | P1 | 0.25d | Senior Backend | Single source of truth |
| NFE-14 | CFOP fixo `5102` ignora reciclagem de vasilhame, comodato, transferência entre filiais | P1 | 2d | Senior Backend + consultor | Resolver CFOP por `tipo_operacao` do pedido |
| NFE-15 | `emitir_nfe_pedido` valida duplicata só em status `autorizada` ou `enviada` — perde caso de `erro_emissao`/`rejeitada` que precisa ser reemitida com novo número | P2 | 0.5d | Senior Backend | Política explícita de reenvio |
| NFE-16 | Sem trace_id / correlation-id nos logs | P2 | 0.5d | Senior Backend | Propagar `request_id` da API |
| NFE-17 | Sem CT-e para transporte do gás | P2 | 5d | Senior Backend + consultor | Avaliar se a empresa transporta com frota própria; se sim, obrigatório |
| NFE-18 | Sem MDF-e | P2 | 4d | Senior Backend + consultor | Depende de NFE-17 |
| NFE-19 | XML autorizado guardado em `TEXT` no Postgres sem política de retenção | P2 | 1d | Senior Backend + DevOps | Mover para object storage (S3/MinIO) com lifecycle de 5 anos |
| NFE-20 | Sem job de polling para NF-e em `enviada` que não voltou autorização | P2 | 1d | Senior Backend | Worker periódico que consulta protocolo |
| NFE-21 | Comodato de vasilhame não modelado | P3 | 3d | Pleno + consultor | Operação típica do segmento, não bloqueia faturamento normal |
| NFE-22 | Migração para emissão própria (sem Unimake) como plano B | P3 | 10d | Senior Backend | Estratégico; mitiga risco de fornecedor único |

**Esforço total para fechar P0+P1 (NFE-01 a NFE-14):** ≈ **22 dias-dev** + 5 dias de consultoria fiscal externa (cobertura paralela aos itens NFE-02, NFE-07, NFE-14, NFE-17/18 e revisão final do XML).

P2 (NFE-15 a NFE-20): +13 dias-dev. P3 (NFE-21, NFE-22): backlog estratégico.

## 5. Recomendação de consultoria fiscal

**Sim — contratar antes do go-live em produção.** Justificativa:

1. **Domínio especializado:** GLP é regime monofásico com ICMS-ST e tem regras estaduais (RICMS-PR Anexo IX) que mudam com frequência. Engenharia interna não tem essa especialização e não deveria ter — é trabalho de contador/auditor fiscal.
2. **Risco financeiro assimétrico:** uma NF-e com CST/CFOP/NCM errado durante 30 dias gera passivo retroativo (multa de 75–150 % do imposto + correção SELIC) que paga o consultor 100×.
3. **Validação cruzada:** o XML produzido hoje precisa ser auditado linha-a-linha contra o Manual de Orientação do Contribuinte v7.00 e contra a NT 2024.001 antes de qualquer emissão real.
4. **Plano de contingência fiscal:** decisão sobre SVC-RS vs. FS-DA depende do perfil de operação (vendas presenciais vs. delivery) e exige assinatura técnica de contador.

Estimativa de custo para a consultoria (referência mercado SP/PR, 2026): **R$ 8 000 – R$ 15 000 por 5 dias úteis de trabalho do consultor**, cobrindo:

- Revisão do XML emitido pelo `gerar_xml_nfe` com os itens NFE-02, NFE-14, NFE-17/18.
- Definição da matriz CFOP × tipo de operação × tipo de cliente.
- Configuração do regime tributário e CSTs corretos para PIS/COFINS/ICMS-ST de GLP.
- Validação do plano de contingência (SVC-RS vs. FS-DA).
- Treinamento de 4h para o time fiscal interno (ou apontamento de processos faltantes).

Esta estimativa **bate** com o que o CTO já levantou para o CEO no relatório de arquitetura (R$ 8–15k em [`ARCHITECTURE_HEALTH_REPORT_2026-04-30.md`](ARCHITECTURE_HEALTH_REPORT_2026-04-30.md#decision-asks-for-ceo)).

## 6. Próximas ações propostas

1. **CTO:** escalar para CEO o pedido de orçamento de consultoria fiscal (R$ 8–15k, 5 dias) — bloqueia NFE-02 / NFE-07 / NFE-14 / NFE-17/18.
2. **Senior Backend (eu):** abrir child issues para NFE-01, NFE-03, NFE-04, NFE-05, NFE-06, NFE-08, NFE-09, NFE-10, NFE-11, NFE-13 (P0 + P1 puramente técnicos, total ≈ 11 dev-days). Propor faseamento dentro do Cycle 3 ("NF-e remediation") já previsto em [`ARCHITECTURE_HEALTH_REPORT_2026-04-30.md`](ARCHITECTURE_HEALTH_REPORT_2026-04-30.md).
3. **Senior Backend:** travar `UNIMAKE_AMBIENTE=2` por validação no `app/config.py` quando `ENVIRONMENT != "production"` **e** garantir que produção falhe ao subir se P0s estiverem abertos (feature flag `nfe_emission_enabled` default `False`).
4. **Senior Backend + Pleno:** escrever testes (NFE-04) cobrindo: happy path, rejeição SEFAZ, timeout Unimake, NF-e duplicada, cancelamento, CC-e — parametrizados por modelo 55/65.
5. **CTO + Consultor:** após Cycle 1, definir plano para NFE-17/18 (CT-e/MDF-e) — só vira P0 se a empresa começar a transportar com frota própria.

## 7. Acceptance criteria desta auditoria

- [x] Documento mergeado em `main`
- [ ] Comentário em [MAX-23](/MAX/issues/MAX-23) com link
- [ ] CTO sinaliza decisão sobre consultoria fiscal (sim/não/orçamento alternativo)
- [ ] Após decisão: criar child issues para NFE-01..NFE-14, atribuir a Senior Backend, sequenciar com [MAX-11](/MAX/issues/MAX-11)

## Referências

- Manual de Orientação do Contribuinte (MOC) NF-e 4.0, v7.00 — Portal Fiscal SEFAZ
- Nota Técnica 2024.001 — eventos e leiautes
- Convênio ICMS 110/07 — combustíveis
- RICMS-PR Anexo IX (substituição tributária combustíveis)
- Lei 9.718/98 art. 4º — PIS/COFINS monofásico para combustíveis
- Documentação Unimake Cloud — `https://inside.unimake.com.br/uninfe/` (em `.env.example`)
- [`ARCHITECTURE_HEALTH_REPORT_2026-04-30.md`](ARCHITECTURE_HEALTH_REPORT_2026-04-30.md) — risco R-05 origem
