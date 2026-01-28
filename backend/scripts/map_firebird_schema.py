#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script FOCADO: Lê apenas a tabela FONE do Firebird 5 + busca por telefone
Compatível com firebird.driver
"""
import sys
import io

# Força UTF-8 no stdout (necessário para Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
import re
import phonenumbers
from phonenumbers import carrier
import firebird.driver as fdb
from firebird.driver import DriverConfig

# AJUSTE O CAMINHO DO fbclient.dll
DriverConfig.fb_client_library = r"C:\Program Files\Firebird\Firebird_5_0\bin\fbclient.dll"

# Configurações de conexão
HOST = "192.168.10.156"
PORT = 3050
DB_PATH = "/var/firebird/Gas.fdb"
USER = "SYSDBA"
PASSWORD = "masterkey"
CHARSET = "WIN1252"  # Encoding original do banco Firebird

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def connect():
    try:
        print(f"Conectando ao Firebird: {HOST}:{PORT} -> {DB_PATH}")
        conn = fdb.connect(
            database=f"{HOST}/{PORT}:{DB_PATH}",
            user=USER,
            password=PASSWORD,
            charset=CHARSET
        )
        logging.info("Conectado ao firebird")
        return conn
    except fdb.DatabaseError as e:
        print(f"Erro ao conectar ao banco? {e}")
        return None



def show_fone_structure(conn):
    print("\n=== Estrutura da tabela FONE ===")
    print(f"\n=== Estrutura da tabela ENDERECO ===")
    query = """
        SELECT
            RF.RDB$FIELD_NAME,
             F.RDB$FIELD_TYPE,
            F.RDB$FIELD_LENGTH,
            RF.RDB$NULL_FLAG,
            RF.RDB$DEFAULT_SOURCE
        FROM RDB$RELATION_FIELDS RF
        JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
        WHERE RF.RDB$RELATION_NAME = 'ENDERECO'
        ORDER BY RF.RDB$FIELD_POSITION
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            for row in cur:
                name = row[0].strip()
                ftype = row[1]
                length = row[2]
                nullable = "NULL" if row[3] is None else "NOT NULL"
                default = row[4].strip() if row[4] else ""
                print(f"  {name:<20} {ftype}({length})  {nullable} {default}")
    except fdb.DatabaseError as e:
        logging.error(f"Erro ao consultar ENDERECO: {e}")

def show_fone_examples(conn, limit=10):
    print(f"\n=== Primeiros {limit} telefones da tabela FONE ===")
    query = """
        SELECT
            RF.RDB$FIELD_NAME,
            F.RDB$FIELD_TYPE,
            F.RDB$FIELD_LENGTH,
            RF.RDB$NULL_FLAG,
            RF.RDB$DEFAULT_SOURCE
        FROM RDB$RELATION_FIELDS RF
        JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
        WHERE TRIM(RF.RDB$RELATION_NAME) = 'FONE'
        ORDER BY RF.RDB$FIELD_POSITION
    """
    try:
         with conn.cursor() as cur:
            cur.execute(query)
            for row in cur:
                name = row[0].strip()
                ftype = row[1]
                length = row[2]
                nullable = "NULL" if row[3] is None else "NOT NULL"
                default = row[4].strip() if row[4] else ""
                print(f"  {name:<20} {ftype}({length})  {nullable} {default}")
    except fdb.DatabaseError as e:
        print(f" Erro ao buscar esturtura da tabela FONE: {e}")

def show_endereco_examples(conn, limit=15):
    print(f"\n=== Primeiros {limit} endereços da tabela ENDERECO ===")
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            ...
    except fdb.DatabaseError as e:
        print(f"Erro ao consultar ENDERECO: {e}")

    query = """
        SELECT
            RF.RDB$FIELD_NAME,
            F.RDB$FIELD_TYPE,
            F.RDB$FIELD_LENGTH,
            RF.RDB$NULL_FLAG,
            RF.RDB$DEFAULT_SOURCE
        FROM RDB$RELATION_FIELDS RF
        JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
        WHERE RF.RDB$RELATION_NAME = 'ENDERECO'
        ORDER BY RF.RDB$FIELD_POSITION
    """
    with conn.cursor() as cur:
        cur.execute(query)
        for row in cur:
            name = row[0].strip()
            ftype = row[1]
            length = row[2]
            nullable = "NULL" if row[3] is None else "NOT NULL"
            default = row[4].strip() if row[4] else ""
            print(f"  {name:<20} {ftype}({length})  {nullable} {default}")



    #with conn.cursor() as cur:
      #  cur.execute(query)
        #for row in cur:
        #   print(
         #       f"ID={row[0]} | Pessoa={row[1]} | Rua='{row[2]}' | Número='{row[3]}' | "
          #      f"Complemento='{row[4]}' | Bairro_ID={row[5]}"
         #   )

def search_by_phone(conn, phone_input):
    phone_clean = re.sub(r'[^0-9]', '', phone_input)
    if len(phone_clean) < 8:
        print("Número muito curto.")
        return

    last8 = phone_clean[-8:]
    print(f"\n🔍 Buscando telefone: {phone_input} → limpo: {phone_clean} (últimos 8: {last8})")

    query = """
        SELECT FIRST 5
            f.ID as FONE_ID,
            f.PESSOA_ID,
            f.NUMERO,
            f.NUMEROPURO,
            p.NOME AS PESSOA_NOME,
            p.POPULAR AS PESSOA_APELIDO,
            c.ID as CLIENTE_ID,
            e.LOGRADOURO,
            e.NUMERO as END_NUMERO,
            e.COMPLEMENTO,
            b.NOME as BAIRRO,
            ci.NOME as CIDADE
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
    with conn.cursor() as cur:
        cur.execute(query, (phone_clean, f"%{last8}%", last8))
        rows = cur.fetchall()

    print(f"Resultados encontrados: {len(rows)}")
    if not rows:
        print("Nenhum resultado. Tente outro número.")
        return

    for row in rows:
        print(f"→ Fone ID: {row[0]} | Pessoa ID: {row[1]}")
        print(f"   Número: {row[2]} | Puro: {row[3]}")
        print(f"   Nome: {row[4]} | Apelido: {row[5]}")
        print(f"   Cliente ID: {row[6]}")
        print(f"   Endereço: {row[7]}, {row[8] or ''} {row[9] or ''}")
        print(f"   Bairro: {row[10]} | Cidade: {row[11]}")
        print("-" * 60)



def validate_phone_number(number_str):
    """Valida e formata números usando phonenumbers"""
    results = []
    try:
        for match in phonenumbers.PhoneNumberMatcher(number_str, "BR"):
            parsed = match.number
            if phonenumbers.is_valid_number(parsed):
                results.append({
                    "original": match.raw_string,
                    "nacional": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
                    "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
                    "operadora": carrier.name_for_number(parsed, "pt-BR")
                })
    except Exception as e:
        print(F"Erro ao validar telefone: {e}")
    return results


def main():
    conn = connect()
    if not conn:
        print("Encerrando script por falha de conexão.")
        return

    show_fone_structure(conn)
    show_fone_examples(conn, limit=10)

    # Exemplo de busca (substitua por um número real do seu banco)
    telefone = "4199954068"
    search_by_phone(conn, telefone)

    # Validação de telefone
    numero_teste = "(41) 9995-4068"
    valid_nums = validate_phone_number(numero_teste)
    if valid_nums:
        print("\n✅ Validação de telefone:")
        for num in valid_nums:
            print(f"Original: {num['original']}")
            print(f"Nacional: {num['nacional']}")
            print(f"E164: {num['e164']}")
            print(f"Operadora: {num['operadora']}")
            print("-" * 40)

    conn.close()
    print("\nFinalizado.")


if __name__ == "__main__":
    main()