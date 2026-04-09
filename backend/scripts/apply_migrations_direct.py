"""
Script de migração direta via psycopg2.
Aplica as 7 migrações novas sem precisar do Docker ou alembic CLI.

Uso:
    python3 backend/scripts/apply_migrations_direct.py
"""

import psycopg2
import psycopg2.extras
import sys

DB_URL = "host=192.168.10.167 port=5433 user=gasadmin password=gasadmin123 dbname=gas_automation"

TARGET_REVISION = "20260325_add_nota_fiscal_tables"

STEPS = []


def step(name):
    def decorator(fn):
        STEPS.append((name, fn))
        return fn
    return decorator


# ── 1. customer_financial + order_profits ─────────────────────────────────────

@step("customer_financial + order_profits")
def s1(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_financial (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            balance         NUMERIC(14,2) NOT NULL DEFAULT 0,
            credit_limit    NUMERIC(14,2) NOT NULL DEFAULT 200,
            total_purchases NUMERIC(14,2) NOT NULL DEFAULT 0,
            total_orders    INTEGER       NOT NULL DEFAULT 0,
            last_purchase_at TIMESTAMPTZ,
            notes           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ,
            CONSTRAINT uq_customer_financial_customer UNIQUE (customer_id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_customer_financial_customer_id ON customer_financial(customer_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_customer_financial_balance      ON customer_financial(balance);")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_profits (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id           UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            revenue            NUMERIC(14,2) NOT NULL DEFAULT 0,
            product_cost       NUMERIC(14,2) NOT NULL DEFAULT 0,
            delivery_cost      NUMERIC(14,2) NOT NULL DEFAULT 0,
            estimated_cost     NUMERIC(14,2) NOT NULL DEFAULT 0,
            profit             NUMERIC(14,2) NOT NULL DEFAULT 0,
            margin_percentage  NUMERIC(6,2)  NOT NULL DEFAULT 0,
            bairro             VARCHAR(100),
            notes              TEXT,
            calculated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at         TIMESTAMPTZ,
            CONSTRAINT uq_order_profit_order UNIQUE (order_id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_order_profits_order_id ON order_profits(order_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_order_profits_bairro   ON order_profits(bairro);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_order_profits_profit   ON order_profits(profit);")


# ── 2. Colunas novas em products (categoria, volume_litros, requer_retorno) ───

@step("colunas categoria/volume_litros/requer_retorno_vasilhame em products")
def s2(cur):
    # categoria
    cur.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS categoria VARCHAR(20) NOT NULL DEFAULT 'gas';
    """)
    # volume_litros
    cur.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS volume_litros INTEGER;
    """)
    # requer_retorno_vasilhame
    cur.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS requer_retorno_vasilhame BOOLEAN NOT NULL DEFAULT true;
    """)
    # Tornar weight_kg nullable (pode falhar silenciosamente se já for nullable)
    try:
        cur.execute("ALTER TABLE products ALTER COLUMN weight_kg DROP NOT NULL;")
    except Exception:
        pass

    cur.execute("CREATE INDEX IF NOT EXISTS ix_products_categoria ON products(categoria);")

    # Preenche volume_litros dos produtos de gás existentes
    cur.execute("UPDATE products SET volume_litros = 13 WHERE code = 'P13';")
    cur.execute("UPDATE products SET volume_litros = 20 WHERE code = 'P20';")
    cur.execute("UPDATE products SET volume_litros = 45 WHERE code = 'P45';")


# ── 3. pix_conciliation_runs + pix_conciliation_items ────────────────────────

@step("pix_conciliation_runs + pix_conciliation_items")
def s3(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pix_conciliation_runs (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conciliation_date   DATE        NOT NULL,
            run_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            total_asaas         INTEGER     NOT NULL DEFAULT 0,
            total_local         INTEGER     NOT NULL DEFAULT 0,
            total_conciliado    INTEGER     NOT NULL DEFAULT 0,
            total_divergencia   INTEGER     NOT NULL DEFAULT 0,
            total_apenas_asaas  INTEGER     NOT NULL DEFAULT 0,
            total_apenas_local  INTEGER     NOT NULL DEFAULT 0,
            valor_asaas         NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            valor_local         NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            status              VARCHAR(30) NOT NULL DEFAULT 'pendente_revisao',
            aprovado_por        INTEGER REFERENCES users(id) ON DELETE SET NULL,
            aprovado_at         TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_pix_conciliation_runs_date ON pix_conciliation_runs(conciliation_date);")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pix_conciliation_items (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id              UUID NOT NULL REFERENCES pix_conciliation_runs(id) ON DELETE CASCADE,
            resultado           VARCHAR(30) NOT NULL,
            asaas_payment_id    VARCHAR(50),
            asaas_amount        NUMERIC(10,2),
            asaas_payer_name    VARCHAR(200),
            asaas_paid_at       TIMESTAMPTZ,
            transaction_id      UUID REFERENCES transactions(id) ON DELETE SET NULL,
            transaction_amount  NUMERIC(10,2),
            order_id            UUID REFERENCES orders(id) ON DELETE SET NULL,
            diferenca           NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            observacao          TEXT,
            resolvido           BOOLEAN NOT NULL DEFAULT false,
            resolvido_por       INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_pix_conciliation_items_run_id         ON pix_conciliation_items(run_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_pix_conciliation_items_run_resultado   ON pix_conciliation_items(run_id, resultado);")


# ── 4. vasilhame_estoque + vasilhame_movimentos ───────────────────────────────

@step("vasilhame_estoque + vasilhame_movimentos")
def s4(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vasilhame_estoque (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tipo           VARCHAR(10) NOT NULL UNIQUE,
            qtd_cheios     INTEGER     NOT NULL DEFAULT 0,
            qtd_vazios     INTEGER     NOT NULL DEFAULT 0,
            qtd_em_campo   INTEGER     NOT NULL DEFAULT 0,
            custo_unitario NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    # Seed inicial
    cur.execute("""
        INSERT INTO vasilhame_estoque (tipo) VALUES ('P13'),('P20'),('P45'),('G20L')
        ON CONFLICT (tipo) DO NOTHING;
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vasilhame_movimentos (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tipo_vasilhame       VARCHAR(10) NOT NULL,
            tipo_movimento       VARCHAR(30) NOT NULL,
            quantidade           INTEGER     NOT NULL,
            custo_unitario       NUMERIC(10,2),
            custo_total          NUMERIC(10,2),
            pedido_id            UUID REFERENCES orders(id) ON DELETE SET NULL,
            entregador_id        INTEGER REFERENCES users(id)  ON DELETE SET NULL,
            observacao           TEXT,
            created_by           INTEGER REFERENCES users(id)  ON DELETE SET NULL,
            saldo_cheios_antes   INTEGER NOT NULL DEFAULT 0,
            saldo_vazios_antes   INTEGER NOT NULL DEFAULT 0,
            saldo_em_campo_antes INTEGER NOT NULL DEFAULT 0,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_vasilhame_movimentos_tipo     ON vasilhame_movimentos(tipo_vasilhame);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_vasilhame_movimentos_tipo_mov ON vasilhame_movimentos(tipo_movimento);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_vasilhame_movimentos_pedido   ON vasilhame_movimentos(pedido_id);")


# ── 5. fiado_entries + fiado_pagamentos ───────────────────────────────────────

@step("fiado_entries + fiado_pagamentos")
def s5(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fiado_entries (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
            order_id            UUID NOT NULL REFERENCES orders(id)    ON DELETE RESTRICT,
            valor_original      NUMERIC(10,2) NOT NULL,
            valor_pago          NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            vencimento          DATE          NOT NULL,
            status              VARCHAR(20)   NOT NULL DEFAULT 'em_aberto',
            cobrado_whatsapp_at TIMESTAMPTZ,
            cobrado_count       INTEGER       NOT NULL DEFAULT 0,
            observacao          TEXT,
            pago_at             TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_fiado_entries_customer_id ON fiado_entries(customer_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_fiado_entries_order_id    ON fiado_entries(order_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_fiado_entries_status      ON fiado_entries(status);")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fiado_pagamentos (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entry_id        UUID NOT NULL REFERENCES fiado_entries(id) ON DELETE CASCADE,
            valor           NUMERIC(10,2) NOT NULL,
            metodo          VARCHAR(30)   NOT NULL,
            asaas_payment_id VARCHAR(100),
            pago_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
            registrado_por  INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_fiado_pagamentos_entry_id ON fiado_pagamentos(entry_id);")


# ── 6. notas_fiscais ──────────────────────────────────────────────────────────

@step("notas_fiscais")
def s6(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notas_fiscais (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tipo                    VARCHAR(5)    NOT NULL DEFAULT '65',
            numero                  INTEGER,
            serie                   VARCHAR(5)    NOT NULL DEFAULT '001',
            chave_acesso            VARCHAR(50),
            status                  VARCHAR(20)   NOT NULL DEFAULT 'rascunho',
            pedido_id               UUID REFERENCES orders(id)    ON DELETE SET NULL,
            customer_id             UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
            emitido_por             INTEGER NOT NULL REFERENCES users(id)     ON DELETE RESTRICT,
            valor_produtos          NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            valor_frete             NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            valor_desconto          NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            valor_total             NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            valor_icms              NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            valor_pis               NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            valor_cofins            NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            xml_enviado             TEXT,
            xml_autorizado          TEXT,
            pdf_danfe_url           VARCHAR(500),
            enviada_whatsapp        BOOLEAN       NOT NULL DEFAULT false,
            enviada_whatsapp_at     TIMESTAMPTZ,
            motivo_rejeicao         TEXT,
            cancelamento_protocolo  VARCHAR(100),
            emitida_at              TIMESTAMPTZ,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_notas_fiscais_pedido_id    ON notas_fiscais(pedido_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_notas_fiscais_customer_id  ON notas_fiscais(customer_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_notas_fiscais_status       ON notas_fiscais(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_notas_fiscais_numero       ON notas_fiscais(numero);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_notas_fiscais_chave_acesso ON notas_fiscais(chave_acesso);")


# ── Atualiza alembic_version ──────────────────────────────────────────────────

@step("atualizar alembic_version para HEAD")
def s7(cur):
    cur.execute("DELETE FROM alembic_version;")
    cur.execute("INSERT INTO alembic_version (version_num) VALUES (%s);", (TARGET_REVISION,))


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    print(f"Conectando ao banco em 192.168.10.167:5433 ...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
    except Exception as e:
        print(f"ERRO ao conectar: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # Verificar versão atual
    cur.execute("SELECT version_num FROM alembic_version;")
    current = cur.fetchone()
    print(f"Versão atual no banco: {current[0] if current else 'nenhuma'}")
    print()

    ok = True
    for name, fn in STEPS:
        print(f"  Aplicando: {name} ...", end=" ", flush=True)
        try:
            fn(cur)
            conn.commit()
            print("OK")
        except Exception as e:
            conn.rollback()
            print(f"ERRO: {e}")
            ok = False
            break

    if ok:
        cur.execute("SELECT version_num FROM alembic_version;")
        final = cur.fetchone()
        print()
        print(f"Versão final no banco: {final[0]}")
        print()
        print("Todas as migrações aplicadas com sucesso!")
        print("Reinicie o backend para que as mudanças entrem em vigor.")
    else:
        print()
        print("Migração interrompida. Corrija o erro e tente novamente.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
