#!/usr/bin/env python3
"""
Script para gerar chaves de segurança fortes.
Uso: python generate_secrets.py
"""
import secrets

def generate_secret_key(length: int = 32) -> str:
    """Gera uma chave secreta forte usando secrets."""
    return secrets.token_hex(length)

def main():
    print("=" * 60)
    print("Gerador de Chaves de Segurança")
    print("=" * 60)
    print()
    
    secret_key = generate_secret_key(32)
    jwt_secret_key = generate_secret_key(32)
    
    print("🔑 Chaves geradas com sucesso!")
    print()
    print("Adicione estas linhas ao seu arquivo .env:")
    print("-" * 60)
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    print("-" * 60)
    print()
    print("⚠️  IMPORTANTE:")
    print("   - NUNCA commite o arquivo .env no git")
    print("   - Use chaves diferentes em cada ambiente")
    print("   - Gere novas chaves para produção")
    print("=" * 60)

if __name__ == "__main__":
    main()
