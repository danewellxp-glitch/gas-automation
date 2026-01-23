# 📊 GUIA DE ACESSO - GRAFANA DASHBOARD

**Dashboard WebSocket Monitoring - Fase 3**  
**Data:** 21 de Janeiro de 2026  
**Status:** ✅ **CONFIGURADO E FUNCIONANDO**

---

## 🎯 **ACESSO RÁPIDO**

### **1. URL do Dashboard**

**Grafana Home:**
```
http://192.168.10.156:3002
```

**Dashboard direto:**
```
http://192.168.10.156:3002/d/gas-websocket-monitoring/gas-automation-websocket-monitoring-fase-3
```

---

### **2. Credenciais de Login**

```
Usuário: admin
Senha: admin123
```

*(ou a senha configurada na variável `GRAFANA_ADMIN_PASSWORD` no `.env`)*

---

## 📈 **O QUE VOCÊ VAI VER NO DASHBOARD**

### **Painel 1: Conexões WebSocket Totais** (Gauge)
- Mostra o número total de conexões ativas
- Limites de alerta:
  - Verde: < 50 conexões
  - Amarelo: 50-100 conexões
  - Vermelho: > 100 conexões

### **Painel 2: Conexões por Role** (Time Series)
- Gráfico de conexões separadas por papel (admin, operator, owner, etc.)
- Mostra tendências ao longo do tempo
- Diferencia por instância do backend

### **Painel 3: Taxa de Mensagens WebSocket** (Time Series)
- Mensagens enviadas vs recebidas por segundo
- Separado por tipo de mensagem
- Útil para identificar picos de tráfego

### **Painel 4: Latência de Broadcast** (Time Series)
- Percentis 95 e 99 da latência
- Limites de alerta:
  - Verde: < 500ms
  - Amarelo: 500ms - 1s
  - Vermelho: > 1s

### **Painel 5: Event Batcher** (Time Series)
- Tamanho médio dos batches (p95)
- Tamanho atual do buffer
- Mostra eficiência do agrupamento de eventos

### **Painel 6: Redis Pub/Sub** (Time Series)
- Taxa de mensagens publicadas
- Taxa de mensagens recebidas de outras instâncias
- Útil para monitorar comunicação entre backends

### **Painel 7: Taxa de Erros WebSocket** (Time Series)
- Percentual de erros em relação ao total de mensagens
- Limite de alerta em 5%
- Crítico em 10%

### **Painel 8: System Uptime** (Gauge)
- Tempo de atividade de cada instância
- Em segundos

---

## 🔧 **NAVEGAÇÃO NO GRAFANA**

### **Passo a Passo:**

1. **Abrir Grafana:**
   ```
   http://192.168.10.156:3002
   ```

2. **Login:**
   - Usuário: `admin`
   - Senha: `admin123`

3. **Navegar para o Dashboard:**
   - **Opção A:** Clicar em "Dashboards" (menu lateral esquerdo) → "Gas Automation" folder → "Gas Automation - WebSocket Monitoring (Fase 3)"
   
   - **Opção B:** Usar o link direto:
     ```
     http://192.168.10.156:3002/d/gas-websocket-monitoring/gas-automation-websocket-monitoring-fase-3
     ```

4. **Ajustar Período de Visualização:**
   - No canto superior direito, você verá "Last 1 hour" (ou similar)
   - Clique para mudar para:
     - Last 5 minutes (visualização em tempo real)
     - Last 15 minutes
     - Last 1 hour (padrão)
     - Last 6 hours
     - Last 24 hours
     - Custom range (personalizado)

5. **Atualização Automática:**
   - Clique no ícone de refresh no canto superior direito
   - Selecione intervalo de auto-refresh:
     - Off (sem atualização automática)
     - 5s (recomendado para monitoramento em tempo real)
     - 10s
     - 30s
     - 1m

---

## 🎨 **PERSONALIZAÇÕES**

### **Editar Dashboard:**

1. Clique no ícone de engrenagem (⚙️) no canto superior direito
2. Selecione "Settings"
3. Você pode:
   - Alterar nome e descrição
   - Modificar variáveis
   - Adicionar novos painéis
   - Reorganizar painéis

### **Adicionar Novo Painel:**

1. Clique em "Add panel" no topo
2. Selecione "Add a new panel"
3. Escolha o datasource: **Prometheus**
4. Escreva query PromQL (exemplos abaixo)
5. Configure visualização
6. Salvar

### **Exemplos de Queries PromQL:**

```promql
# Total de conexões WebSocket
sum(websocket_connections_total{role="all"})

# Conexões por role
websocket_connections_total{role!="all"}

# Taxa de mensagens enviadas (por segundo)
rate(websocket_messages_sent_total[5m])

# Latência p95 de broadcasts
histogram_quantile(0.95, rate(websocket_broadcast_duration_seconds_bucket[5m]))

# Buffer do Event Batcher
event_batcher_buffer_size

# Mensagens Redis Pub/Sub
rate(redis_pubsub_messages_published[5m])

# Taxa de erro
rate(websocket_errors_total[5m]) / (rate(websocket_messages_sent_total[5m]) + rate(websocket_messages_received_total[5m]))

# Uptime
system_uptime_seconds
```

---

## 🚨 **ALERTAS**

O sistema possui **20 regras de alertas** configuradas no Prometheus.

### **Ver Alertas Ativos:**

1. No Grafana, vá em "Alerting" (menu lateral)
2. Clique em "Alert rules"
3. Você verá todas as regras configuradas

### **Alertas Críticos (🔴):**
- Conexões > 200 por instância
- Taxa de erro > 10%
- Latência > 1 segundo
- Redis Pub/Sub parou de funcionar
- Event Batcher travado
- Instância backend down

### **Alertas de Warning (⚠️):**
- Conexões > 100 por instância
- Taxa de erro > 5%
- Latência > 500ms
- Alta taxa de desconexões

---

## 📊 **INTERPRETAÇÃO DOS DADOS**

### **Valores Normais (Sistema Saudável):**

```
Conexões totais:           < 50
Taxa de mensagens:         < 10/s
Latência (p95):           < 50ms
Taxa de erros:            < 1%
Buffer batcher:           < 10
Redis Pub/Sub:            Mensagens fluindo
Uptime:                   > 1 hora
```

### **Valores de Atenção (Monitorar):**

```
Conexões totais:           50-100
Taxa de mensagens:         10-50/s
Latência (p95):           50-200ms
Taxa de erros:            1-5%
Buffer batcher:           10-30
```

### **Valores Críticos (Ação Necessária):**

```
Conexões totais:           > 100
Taxa de mensagens:         > 50/s
Latência (p95):           > 500ms
Taxa de erros:            > 5%
Buffer batcher:           > 40
```

**Ações recomendadas para valores críticos:**
1. Verificar logs do backend: `docker logs gas_backend`
2. Verificar uso de CPU/memória: `docker stats`
3. Considerar adicionar mais instâncias do backend
4. Verificar conexões de rede (Redis, PostgreSQL)

---

## 🔍 **TROUBLESHOOTING**

### **Dashboard não aparece:**

```bash
# Verificar se Grafana está rodando
docker ps | grep grafana

# Reiniciar Grafana
docker-compose restart grafana

# Ver logs
docker logs gas_grafana --tail 50
```

### **Métricas não aparecem:**

1. **Verificar Prometheus:**
   ```bash
   # Verificar se Prometheus está coletando
   curl http://192.168.10.156:9090/api/v1/targets
   
   # Verificar se backend expõe métricas
   curl http://192.168.10.156:8000/metrics | grep websocket_
   ```

2. **Verificar Datasource no Grafana:**
   - Ir em Configuration → Data sources
   - Verificar "Prometheus" está configurado
   - Testar conexão: "Test" deve retornar "Data source is working"

### **Painel em branco:**

1. Verificar período de visualização (canto superior direito)
2. Alterar para "Last 5 minutes"
3. Gerar alguma atividade no sistema (conectar WebSocket, criar pedido)
4. Aguardar 15-30 segundos para Prometheus coletar métricas

---

## 🎯 **MONITORAMENTO EM TEMPO REAL**

Para monitorar o sistema em tempo real:

1. **Abrir Dashboard:**
   ```
   http://192.168.10.156:3002/d/gas-websocket-monitoring
   ```

2. **Configurar auto-refresh:** 5 segundos

3. **Ajustar período:** "Last 5 minutes"

4. **Tela cheia:** Pressione `F` ou clique em "Fullscreen"

5. **TV Mode:** Para exibir em monitor dedicado, adicione `?kiosk` na URL:
   ```
   http://192.168.10.156:3002/d/gas-websocket-monitoring?kiosk
   ```

---

## 📱 **ACESSO MOBILE**

O Grafana é responsivo e funciona bem em mobile:

```
http://192.168.10.156:3002
```

**Dica:** Adicione aos favoritos do navegador mobile para acesso rápido.

---

## 🔐 **SEGURANÇA**

### **Alterar Senha:**

1. Ir em "Profile" (ícone de usuário)
2. Selecionar "Change password"
3. Definir nova senha forte

### **Criar Usuários:**

1. Ir em "Configuration" → "Users"
2. Clique em "New user"
3. Defina permissões (Viewer, Editor, Admin)

### **API Key (para integrações):**

1. Ir em "Configuration" → "API Keys"
2. Clique em "New API key"
3. Defina nome e role
4. Copiar chave gerada

---

## 📚 **RECURSOS ADICIONAIS**

### **Documentação Oficial:**
- Grafana Docs: https://grafana.com/docs/grafana/latest/
- PromQL Guide: https://prometheus.io/docs/prometheus/latest/querying/basics/

### **Exemplos de Dashboards:**
- Grafana Dashboards: https://grafana.com/grafana/dashboards/

### **Arquivos do Projeto:**
- Dashboard JSON: `grafana/dashboards/websocket.json`
- Regras de Alertas: `prometheus/alerts.yml`
- Métricas Backend: `backend/app/metrics.py`

---

## ✅ **CHECKLIST DE VERIFICAÇÃO**

- [ ] Grafana acessível em http://192.168.10.156:3002
- [ ] Login funciona com admin/admin123
- [ ] Dashboard "Gas Automation - WebSocket Monitoring (Fase 3)" aparece
- [ ] Todos os 8 painéis carregam dados
- [ ] Prometheus datasource está conectado
- [ ] Métricas estão sendo coletadas (Backend endpoint `/metrics` responde)
- [ ] Alertas configurados em Prometheus
- [ ] Auto-refresh configurado (5s recomendado)

---

**Dashboard configurado com sucesso!** 🎉

Para suporte, consulte:
- `FASE_3_COMPLETA.md` - Documentação completa da Fase 3
- Logs: `docker logs gas_grafana`
- Métricas: `curl http://192.168.10.156:8000/metrics`

---

**Última atualização:** 21 de Janeiro de 2026
