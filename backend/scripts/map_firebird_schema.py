#!/usr/bin/env python3
"""
Script para mapear o schema do Firebird da Gasmaster.
Conecta ao banco e lista todas as tabelas e suas estruturas.
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import fdb
except ImportError:
    print("❌ Biblioteca fdb não instalada. Instale com: pip install fdb")
    sys.exit(1)

# Configurações de conexão
FIREBIRD_HOST = "192.168.10.156"
FIREBIRD_DATABASE = "/var/firebird/Gas.fdb"
FIREBIRD_USER = "SYSDBA"
FIREBIRD_PASSWORD = "masterkey"
FIREBIRD_PORT = 3050

def get_connection():
    """Cria conexão com Firebird."""
    try:
        # Formato do fdb: host/port:database ou host:database
        # Para caminho remoto, usar: host/port:caminho_absoluto
        dsn = f"{FIREBIRD_HOST}/{FIREBIRD_PORT}:{FIREBIRD_DATABASE}"
        print(f"   Tentando DSN: {dsn}")
        
        # Tentar diferentes formatos de conexão
        try:
            conn = fdb.connect(
                dsn=dsn,
                user=FIREBIRD_USER,
                password=FIREBIRD_PASSWORD,
                charset="UTF8"
            )
            return conn
        except Exception as e1:
            # Tentar formato alternativo sem porta
            print(f"   Tentando formato alternativo...")
            dsn2 = f"{FIREBIRD_HOST}:{FIREBIRD_DATABASE}"
            try:
                conn = fdb.connect(
                    host=FIREBIRD_HOST,
                    database=FIREBIRD_DATABASE,
                    user=FIREBIRD_USER,
                    password=FIREBIRD_PASSWORD,
                    charset="UTF8"
                )
                return conn
            except Exception as e2:
                # Tentar com caminho completo
                print(f"   Tentando com caminho completo...")
                conn = fdb.connect(
                    host=FIREBIRD_HOST,
                    port=FIREBIRD_PORT,
                    database=FIREBIRD_DATABASE,
                    user=FIREBIRD_USER,
                    password=FIREBIRD_PASSWORD,
                    charset="UTF8"
                )
                return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        print(f"   Tipos de erro: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def list_tables(conn):
    """Lista todas as tabelas do banco."""
    cursor = conn.cursor()
    
    # Query para listar tabelas do Firebird
    query = """
        SELECT RDB$RELATION_NAME
        FROM RDB$RELATIONS
        WHERE RDB$SYSTEM_FLAG = 0
        AND RDB$RELATION_TYPE = 0
        ORDER BY RDB$RELATION_NAME
    """
    
    cursor.execute(query)
    tables = []
    for row in cursor:
        table_name = row[0].strip()
        tables.append(table_name)
    
    cursor.close()
    return tables

def get_table_structure(conn, table_name):
    """Obtém estrutura de uma tabela."""
    cursor = conn.cursor()
    
    query = """
        SELECT
            RF.RDB$FIELD_NAME,
            F.RDB$FIELD_TYPE,
            F.RDB$FIELD_LENGTH,
            F.RDB$FIELD_SCALE,
            RF.RDB$NULL_FLAG,
            RF.RDB$DEFAULT_SOURCE
        FROM RDB$RELATION_FIELDS RF
        JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
        WHERE RF.RDB$RELATION_NAME = ?
        ORDER BY RF.RDB$FIELD_POSITION
    """
    
    cursor.execute(query, (table_name,))
    columns = []
    for row in cursor:
        col_name = row[0].strip()
        field_type = row[1]
        field_length = row[2]
        field_scale = row[3] if row[3] else 0
        is_nullable = row[4] is None
        default = row[5].strip() if row[5] else None
        
        # Mapear tipos do Firebird
        type_map = {
            7: "SMALLINT",
            8: "INTEGER",
            10: "FLOAT",
            12: "DATE",
            13: "TIME",
            14: "CHAR",
            16: "BIGINT",
            27: "DOUBLE PRECISION",
            35: "TIMESTAMP",
            37: "VARCHAR",
            261: "BLOB"
        }
        
        sql_type = type_map.get(field_type, f"TYPE_{field_type}")
        if field_type in (14, 37):  # CHAR ou VARCHAR
            sql_type = f"{sql_type}({field_length})"
        
        columns.append({
            "name": col_name,
            "type": sql_type,
            "nullable": is_nullable,
            "default": default
        })
    
    cursor.close()
    return columns

def get_sample_data(conn, table_name, limit=5):
    """Obtém dados de exemplo de uma tabela."""
    cursor = conn.cursor()
    
    try:
        query = f'SELECT FIRST {limit} * FROM "{table_name}"'
        cursor.execute(query)
        
        # Obter nomes das colunas
        columns = [desc[0].strip() for desc in cursor.description]
        
        rows = []
        for row in cursor:
            rows.append(dict(zip(columns, row)))
        
        cursor.close()
        return rows
    except Exception as e:
        cursor.close()
        return None

def main():
    print("=" * 80)
    print("🔍 MAPEAMENTO DO SCHEMA FIREBIRD - GASMASTER")
    print("=" * 80)
    print()
    
    # Conectar
    print(f"📡 Conectando ao Firebird...")
    print(f"   Host: {FIREBIRD_HOST}")
    print(f"   Database: {FIREBIRD_DATABASE}")
    print()
    
    conn = get_connection()
    print("✅ Conectado com sucesso!")
    print()
    
    # Listar tabelas
    print("📋 Listando tabelas...")
    tables = list_tables(conn)
    print(f"   Encontradas {len(tables)} tabelas")
    print()
    
    # Tabelas importantes para mapear
    important_tables = [
        "PRODUTOS", "PRODUTO", "PROD",
        "CLIENTES", "CLIENTE", "CLI",
        "PEDIDOS", "PEDIDO", "PED",
        "VENDAS", "VENDA", "VDA",
        "ESTOQUE", "STOCK",
        "BAIRROS", "BAIRRO",
        "PRECOS", "PRECO"
    ]
    
    # Filtrar tabelas importantes
    found_important = []
    for table in tables:
        for important in important_tables:
            if important.upper() in table.upper():
                found_important.append(table)
                break
    
    print("🎯 Tabelas importantes encontradas:")
    for table in found_important:
        print(f"   ✓ {table}")
    print()
    
    # Mapear estrutura das tabelas importantes
    print("=" * 80)
    print("📊 ESTRUTURA DAS TABELAS")
    print("=" * 80)
    print()
    
    for table in found_important[:10]:  # Limitar a 10 para não ficar muito longo
        print(f"📦 TABELA: {table}")
        print("-" * 80)
        
        columns = get_table_structure(conn, table)
        print(f"   Colunas: {len(columns)}")
        print()
        
        for col in columns:
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col["default"] else ""
            print(f"   • {col['name']:<30} {col['type']:<20} {nullable}{default}")
        
        print()
        
        # Mostrar dados de exemplo
        sample = get_sample_data(conn, table, limit=2)
        if sample:
            print("   📄 Exemplo de dados:")
            for i, row in enumerate(sample, 1):
                print(f"      [{i}] {dict(list(row.items())[:3])}")  # Mostrar apenas 3 primeiras colunas
        print()
        print()
    
    # Listar todas as tabelas
    print("=" * 80)
    print("📋 TODAS AS TABELAS DO BANCO")
    print("=" * 80)
    print()
    for i, table in enumerate(tables, 1):
        print(f"   {i:3d}. {table}")
    
    conn.close()
    print()
    print("=" * 80)
    print("✅ Mapeamento concluído!")
    print("=" * 80)

if __name__ == "__main__":
    main()
