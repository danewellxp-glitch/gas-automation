#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script FOCADO:
- Lê estrutura das tabelas FONE e ENDERECO
- Busca cliente por telefone no Firebird 5
Compatível com firebird.driver
"""

import sys
import io
import logging
import re
import os

import phonenumbers
from phonenumbers import carrier

import firebird.driver as fdb
from firebird.driver import DriverConfig

# ──────────────────────────────────────────────────────────────
# FORÇA UTF-8 NO STDOUT (Windows)
# ──────────────────────────────────────────────────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ──────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DO FIREBIRD CLIENT
# ──────────────────────────────────────────────────────────────
DriverConfig.fb_client_library = (
    r"C:\Program Files\Firebird\Firebird_5_0\bin\fbclient.dll"
)

# ──────────────────────────────────────────────────────────────
# CONFIGURAÇÕES DE CONEXÃO (SEM SYSDBA)
# ──────────────────────────────────────────────────────────────
HOST = "192.168.10.167"
PORT = 3050
DB_PATH = "/var/firebird/Gas.fdb"

USER = os.getenv("FIREBIRD_USER", "GAS_AUTOMATION")
PASSWORD = os.getenv("FIREBIRD_PASSWORD")

CHARSET = "UTF8"

if not PASSWORD:
    raise RuntimeError(
        "Variável de ambiente FIREBIRD_PASSWORD não definida"
    )

# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ──────────────────────────────────────────────────────────────
def connect():
    try:
        logging.info("Conectando ao Firebird...")
        conn = fdb.connect(
            database=f"{HOST}/{PORT}:{DB_PATH}",
            user=USER,
            password=PASSWORD,
            charset=CHARSET,
        )
        logging.info("Conexão estabelecida com sucesso")
        return conn
    except fdb.DatabaseError as e:
        logging.exception("Erro ao conectar ao Firebird")
        return None


# ──────────────────────────────────────────────────────────────
def show_table_structure(conn, table_name):
    print(f"\n=== Estrutura da tabela {table_name} ===")

    query = """
        SELECT
            RF.RDB$FIELD_NAME,
            F.RDB$FIELD_TYPE,
            F.RDB$FIELD_LENGTH,
            RF.RDB$NULL_FLAG,
            RF.RDB$DEFAULT_SOURCE
        FROM RDB$RELATION_FIELDS RF
        JOIN RDB$FIELDS F
          ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
        WHERE TRIM(RF.RDB$RELATION_NAME) = ?
        ORDER BY RF.RDB$FIELD_POSITION
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query, (table_name,))
            for row in cur:
                name = row[0].strip()
                ftype = row[1]
                length = row[2]
                nullable = "NULL" if row[3] is None else "NOT NULL"
                default = row[4].strip() if row[4] else ""
                print(f"  {name:<20} {ftype}({length}) {nullable} {default}")
    except fdb.DatabaseError:
        logging.exception(f"Erro ao consultar estrutura da tabela {table_name}")


# ──────────────────────────────────────────────────────────────
def search_by_phone(conn, phone_input):
    phone_clean = re.sub(r"\D", "", phone_input)

    if len(phone_clean) < 8:
        logging.warning("Número muito curto para busca")
        return

    last8 = phone_clean[-8:]

    logging.info(
        "Buscando telefone %s (limpo=%s, últimos8=%s)",
        phone_input,
        phone_clean,
        last8,
    )

    query = """
        SELECT FIRST 5
            f.ID,
            f.PESSOA_ID,
            f.NUMERO,
            f.NUMEROPURO,
            p.NOME,
            p.POPULAR,
            c.ID,
            e.LOGRADOURO,
            e.NUMERO,
            e.COMPLEMENTO,
            b.NOME,
            ci.NOME
        FROM FONE f
        JOIN PESSOA p ON f.PESSOA_ID = p.ID
        JOIN CLIENTE c ON p.ID = c.PESSOA_ID
        LEFT JOIN ENDERECO e ON p.ID = e.PESSOA_ID
        LEFT JOIN BAIRRO b ON e.BAIRRO_ID = b.ID
        LEFT JOIN CIDADE ci ON b.CIDADE_ID = ci.ID
        WHERE f.NUMEROPURO = ?
           OR f.NUMEROPURO LIKE ?
           OR f.NUMERO CONTAINING ?
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query, (phone_clean, f"%{last8}%", last8))
            rows = cur.fetchall()
    except fdb.DatabaseError:
        logging.exception("Erro ao buscar telefone")
        return

    print(f"\nResultados encontrados: {len(rows)}")

    for row in rows:
        print(f"→ Fone ID: {row[0]} | Pessoa ID: {row[1]}")
        print(f"   Número: {row[2]} | Puro: {row[3]}")
        print(f"   Nome: {row[4]} | Apelido: {row[5]}")
        print(f"   Cliente ID: {row[6]}")
        print(f"   Endereço: {row[7]}, {row[8] or ''} {row[9] or ''}")
        print(f"   Bairro: {row[10]} | Cidade: {row[11]}")
        print("-" * 60)


# ──────────────────────────────────────────────────────────────
def validate_phone_number(number_str):
    results = []

    try:
        for match in phonenumbers.PhoneNumberMatcher(number_str, "BR"):
            parsed = match.number
            if phonenumbers.is_valid_number(parsed):
                results.append(
                    {
                        "original": match.raw_string,
                        "nacional": phonenumbers.format_number(
                            parsed,
                            phonenumbers.PhoneNumberFormat.NATIONAL,
                        ),
                        "e164": phonenumbers.format_number(
                            parsed,
                            phonenumbers.PhoneNumberFormat.E164,
                        ),
                        "operadora": carrier.name_for_number(
                            parsed, "pt-BR"
                        ),
                    }
                )
    except Exception:
        logging.exception("Erro ao validar telefone")

    return results


# ──────────────────────────────────────────────────────────────
def main():
    conn = connect()
    if not conn:
        return

    try:
        show_table_structure(conn, "FONE")
        show_table_structure(conn, "ENDERECO")

        search_by_phone(conn, "4199954068")

        for info in validate_phone_number("(41) 9995-4068"):
            print("\n✅ Telefone validado:")
            for k, v in info.items():
                print(f"{k}: {v}")
    finally:
        conn.close()
        logging.info("Conexão encerrada")

    print("\nFinalizado.")


if __name__ == "__main__":
    main()