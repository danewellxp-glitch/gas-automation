# Firebase Push Notifications - Configuração

## Arquivos diferentes

| Arquivo | Uso | Onde fica |
|---------|-----|-----------|
| **google-services.json** | App Android (Firebase SDK client) | `frontend/android/` ou raiz – usado pelo APK |
| **firebase-credentials.json** | Backend (Firebase Admin SDK) | `backend/` – usado para enviar push |

O **backend precisa do service account**, não do `google-services.json`.

## Configuração

1. **Obter o service account**  
   Firebase Console → Project Settings → Service Accounts → **Generate new private key**  
   Baixe o JSON (ex.: `gas-driver-404d8-firebase-adminsdk-xxxxx.json`).

2. **Colocar no backend**
   ```bash
   # Copiar para o nome esperado
   cp gas-driver-404d8-firebase-adminsdk-*.json backend/firebase-credentials.json
   ```
   Ou configurar o caminho em `FIREBASE_CREDENTIALS`.

3. **Variável de ambiente** (Docker)
   ```env
   FIREBASE_CREDENTIALS=/app/firebase-credentials.json
   ```
   Ou em `.env` para outro caminho.

4. **Backend sem credenciais**
   - O backend sobe normalmente
   - Push fica desabilitado (apenas log de aviso)
   - `firebase-admin` continua em `requirements.txt`; a inicialização é opcional
