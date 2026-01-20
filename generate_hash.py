#!/usr/bin/env python3
"""Gera hash da senha para inserir no banco de dados"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

password = "Admin@123456"
hashed = pwd_context.hash(password)
print(f"Senha: {password}")
print(f"Hash: {hashed}")
