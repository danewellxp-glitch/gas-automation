# Gas Automation

Sistema de automação de pedidos de gás via WhatsApp, com dashboards operacionais e executivos, entregas (drivers) e integrações com pagamentos e ERP.

## Visão geral (executiva)

O **Gas Automation** organiza a operação de uma distribuidora de gás em um fluxo único:

- **Cliente faz pedido pelo WhatsApp** (bot/fluxo guiado).
- **Operação valida, aprova e despacha** via painel.
- **Entregador recebe e atualiza status em tempo real**.
- **Pagamentos e integrações** (ex.: Asaas e Firebird/ERP) podem ser automatizados.

## Principais funcionalidades

- **Pedidos**
  - Criação por WhatsApp (fluxo com máquina de estados)
  - Criação manual via dashboard (operador)
  - Status: `pending` -> `paid` -> `preparing` -> `dispatched` -> `delivered` (ou `cancelled`)
  - Exportação (CSV) e relatórios

- **WhatsApp (WAHA)**
  - Webhook de mensagens recebidas
  - Envio de respostas (texto, botões, etc.)

- **Pagamentos (Asaas)**
  - Cobrança e atualização de status via webhook

- **Entrega / Driver**
  - Gestão de entregas, atribuição de driver e tracking operacional
  - Painel do entregador (driver)
  - Logs de tempo do driver (time tracking)

- **Tempo real (WebSocket)**
  - Atualizações ao vivo para dashboards
  - Otimizações para escala: filtros por role/bairro, rate limiting, heartbeat, batching e bridge Redis

- **Integração com ERP (Firebird)**
  - Sincronização e exportação fiscal/operacional (quando habilitado)

- **Observabilidade**
  - Métricas Prometheus (endpoint protegido)
  - Dashboards Grafana

## Arquitetura (alto nível)

```
Cliente (WhatsApp) -> WAHA -> Webhook -> Flow Engine -> PostgreSQL
                                      -> Asaas (pagamentos)
                                      -> WebSocket -> Dashboards (Admin/Owner/Operador/Driver)
                                      -> Firebird (ERP) (opcional)

Infra: Docker Compose + Traefik + Redis + Prometheus/Grafana
```

## Stack

- **Backend**: Python + FastAPI + SQLAlchemy/Alembic
- **Banco**: PostgreSQL
- **Cache/Mensageria**: Redis (inclui Pub/Sub para WebSocket)
- **Frontend**: React + Vite + TailwindCSS
- **Integrações**: WAHA (WhatsApp), Asaas (pagamentos), Firebird (ERP)
- **Observabilidade**: Prometheus + Grafana
- **Infra**: Docker Compose (com Traefik)

## Perfis (RBAC)

| Role | Objetivo |
|------|----------|
| `admin` | Administração total do sistema |
| `owner` | Visão executiva (KPIs, relatórios) |
| `operator` | Operação diária (pedidos, conversas, despacho) |
| `driver` | Entregas e atualização de status |

## Quickstart (Docker)

Pré-requisitos: Docker + Docker Compose.

```bash
docker-compose up -d
docker-compose ps
```

## URLs (ambiente padrão)

- **Frontend**: `http://localhost:3001`
- **Backend API**: `http://localhost:8000`
- **Swagger**: `http://localhost:8000/docs`
- **WAHA**: `http://localhost:3000`
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3002`

> Em rede/local, substitua `localhost` pelo IP do servidor (ex.: `192.168.10.156`).

## Variáveis de ambiente (essenciais)

As variáveis são lidas do `.env` (veja `backend/app/config.py` e `docker-compose.yml`).

- **Segurança**
  - `SECRET_KEY` (mínimo 32 chars)
  - `JWT_SECRET_KEY` (mínimo 32 chars)
  - `METRICS_TOKEN` (protege `/metrics`)

- **Banco/Cache**
  - `DATABASE_URL`
  - `REDIS_URL`

- **Integrações**
  - `WAHA_API_KEY`
  - `ASAAS_API_KEY` (se usar pagamentos)
  - `FIREBIRD_HOST`, `FIREBIRD_DATABASE`, `FIREBIRD_USER`, `FIREBIRD_PASSWORD` (se usar Firebird)

## Desenvolvimento (local sem Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Escalabilidade (9.000+ pedidos/semana)

O backend inclui melhorias específicas para volume e tempo real:

- **WebSocket escalável**: filtros por role/bairro, deduplicação por usuário, heartbeat e rate limiting.
- **Event batching**: reduz significativamente o volume de mensagens em picos.
- **Redis WebSocket Bridge**: suporte a múltiplas instâncias do backend via Redis Pub/Sub.
- **Paginação**: endpoints paginados para evitar carregar ?tudo? no frontend.

Verificação técnica: `docs/relatorios/VERIFICACAO_CAPACIDADE_9000_PEDIDOS_28JAN2026.md`.

## Documentação

- **Relatório executivo do sistema**: `docs/resumos/RELATORIO_EXECUTIVO_SISTEMA.md`
- **Resumo 21/Jan (sprint/escala/segurança)**: `docs/resumos/RELATORIO_EXECUTIVO_DIA_21_JAN_2026.md`
- **Escalabilidade (fases 1/2)**: `docs/planos/ESCALABILIDADE_COMPLETA_FASES_1_2.md`

## Troubleshooting

- **Frontend ?Failed to fetch? no login**: normalmente é backend fora do ar ou rede/porta bloqueada. Verifique `http://<host>:8000/health`.
- **Backend com erro de OpenCV/NumPy**: reconstruir imagem do backend com dependências compatíveis (ver `backend/requirements.txt`).
- **Login redireciona e fica em branco**: normalmente token expirado no navegador; o frontend deve limpar e voltar ao `/login`.

## Licença

Proprietary ? All rights reserved.

