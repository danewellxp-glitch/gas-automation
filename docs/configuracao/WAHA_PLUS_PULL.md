# WAHA Plus oficial – como baixar e usar

O projeto está configurado para a imagem **devlikeapro/waha-plus:latest** (WAHA Plus oficial), que suporta botões e listas interativas.

## Imagem no docker-compose

- **Imagem:** `devlikeapro/waha-plus:latest`
- **Engine:** WEBJS (Chromium) – já definido em `WAHA_DEFAULT_ENGINE`
- **CPU:** use a tag que corresponda ao seu servidor (x86: `latest`; ARM: ver no portal)

## Primeira vez: fazer login, pull e logout

A imagem é privada. Use a **key** só para baixar; não guarde a key no repositório.

1. **Login** (substitua `SUA_KEY` pela key que você recebeu no portal):

   ```bash
   docker login -u devlikeapro -p SUA_KEY
   ```

2. **Baixar a imagem e subir o serviço:**

   ```bash
   docker-compose pull waha
   docker-compose up -d waha
   ```

3. **Logout** (importante: fazer depois do pull):

   ```bash
   docker logout
   ```

Depois do pull, a imagem fica no cache local; o container sobe normalmente sem estar logado.

## Onde colocar a key (opcional)

Se quiser automatizar o pull (ex.: em outro servidor ou CI), use a key em variável de ambiente e **nunca** faça commit dela:

- Crie ou edite `.env` na raiz do projeto (o `.env` já está no `.gitignore`).
- Adicione algo como:  
  `WAHA_PLUS_PULL_KEY=sua_key_aqui`
- Use só em scripts que fazem `docker login` → `docker-compose pull waha` → `docker logout`, e não commite o `.env`.

## Configuração do serviço

O `docker-compose.yml` já deixa o WAHA Plus alinhado com o projeto:

- **WEBJS** como engine padrão.
- **Webhook** apontando para o backend: `http://backend:8000/webhooks/waha`.
- **Redis** para sessão/cache.
- **Porta 3000** e volume `waha_data` para persistir a sessão do WhatsApp.

Após o primeiro `up`, acesse o dashboard (por exemplo `http://localhost:3000` ou `http://waha.localhost`) e escaneie o QR Code para vincular o número.

## Versões e CPU

- **Versão:** `latest` no compose; no portal você pode escolher outra tag se precisar.
- **CPU:** em servidor **ARM** (ex.: Raspberry), confira no portal da devlikeapro se existe tag específica (ex.: `devlikeapro/waha-plus:latest-arm`) e altere a linha `image` no `docker-compose.yml` se necessário.
