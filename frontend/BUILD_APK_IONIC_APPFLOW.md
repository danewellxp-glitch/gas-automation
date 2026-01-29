# Build APK na nuvem com Ionic AppFlow (Capacitor)

O frontend já está configurado com **Capacitor** e pronto para build na nuvem via **Ionic AppFlow**.

- **IP da API:** `192.168.10.156:8000` (em `.env.production` e no app)
- **Ícones:** copiados de `mobile-app/AppIcons` para `android/app/src/main/res`
- **App ID (package):** `com.gasautomation.driver` | **App Name:** Gas Driver  
- **Ionic App ID:** coloque o ID do app que você criou no dashboard (ex.: `a1b2c3d4`) no comando `ionic link --app-id=SEU_APP_ID_AQUI`

---

## O que já foi feito

1. **`.env.production`** – `VITE_API_URL`, `VITE_WS_URL` etc. apontando para `http://192.168.10.156:8000`
2. **`package.json`** – `homepage: "."` e nome `gas-driver`; scripts `cap:sync` e `cap:android`
3. **Capacitor** – `@capacitor/core`, `@capacitor/cli`, `@capacitor/android` instalados
4. **`capacitor.config.json`** – appId `com.gasautomation.driver`, webDir `dist-build`, server (allowNavigation para 192.168.10.156), SplashScreen
5. **Plataforma Android** – `npx cap add android` e `npx cap sync` já rodados
6. **Ícones** – ícones de `mobile-app/AppIcons/android` copiados para `android/app/src/main/res` (mipmap-*)

---

## Pré-requisitos

- Conta em [Ionic](https://ionic.io/signup) (grátis)
- App criado no [Dashboard Ionic](https://dashboard.ionicframework.com/) (New App → Nome: **Gas Driver** → Skip Git por enquanto)
- **Anote o App ID** do app (ex.: `a1b2c3d4`) no dashboard

---

## Comandos: primeira vez (configuração)

```bash
# 1. Entrar no frontend
cd frontend

# 2. Build e sync (já usa .env.production)
npm run build
npx cap sync

# 3. Instalar Ionic CLI (global)
npm install -g @ionic/cli

# 4. Login no Ionic
ionic login
# Email e senha da conta Ionic

# 5. Vincular ao app no Ionic (use o App ID que você anotou)
ionic link --app-id=SEU_APP_ID_AQUI

# 6. Git (obrigatório para o AppFlow enviar o build)
git init
git add .
git commit -m "Initial commit - Gas Driver Capacitor"

# 7. Build na nuvem (APK)
ionic package build android --type=apk
```

Quando o build terminar, o CLI mostra um **link para download do APK**. Também aparece em: https://dashboard.ionicframework.com/ → seu app → Builds.

---

## Comandos: próximas vezes (atualizações)

```bash
cd frontend

# Alterar código, depois:
npm run build
npx cap sync

# (Opcional) Incrementar versão em android/app/build.gradle:
# versionCode 2
# versionName "1.1.0"

git add .
git commit -m "Versão 1.1.0 - descrição"
ionic package build android --type=apk
```

---

## Scripts úteis no `package.json`

- `npm run build` – gera `dist-build` (Vite)
- `npm run cap:sync` – build + `npx cap sync`
- `npm run cap:android` – abre o projeto Android no Android Studio (se quiser build local)

---

## Troubleshooting

| Erro | Solução |
|------|--------|
| `No Git repository found` | `git init` e `git add .` + `git commit -m "..."` |
| `Not logged in` | `ionic login` |
| `App not linked` | `ionic link --app-id=SEU_APP_ID` |
| CORS no backend | Backend já deve ter CORS; se precisar, `allow_origins=["*"]` no FastAPI |
| API não carrega no app | Celular na mesma rede do servidor; IP `192.168.10.156` acessível |

---

## Alterar IP da API

1. Edite `frontend/.env.production` e altere `VITE_API_URL`, `VITE_WS_URL`, etc.
2. Rode de novo: `npm run build` e `npx cap sync` antes do próximo `ionic package build android --type=apk`.
