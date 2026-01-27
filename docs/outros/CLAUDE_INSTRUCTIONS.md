# Instruções para o Claude AI

Você está analisando um projeto chamado gas-automation.

Objetivos:
- Revisar a arquitetura geral do projeto
- Identificar código duplicado ou mal estruturado
- Reescrever trechos quando necessário mantendo a lógica
- Sugerir melhorias de segurança, principalmente autenticação e variáveis de ambiente
- NÃO quebrar compatibilidade com o código atual

Contexto:
- Backend em FastAPI
- Integração com WhatsApp (Evolution API / WAHA)
- Uso de .env para configurações sensíveis

Regras:
- Não inventar arquivos que não existam
- Sempre respeitar a estrutura atual do projeto
- Quando sugerir mudanças, mostrar exemplos claros de código
