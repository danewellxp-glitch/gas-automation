"""seed_financeiro_estoque_users

Revision ID: 20260324_seed_financeiro_estoque_users
Revises: 20260324_create_stock_module
Create Date: 2026-03-24 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

revision = "20260324_seed_financeiro_estoque_users"
down_revision = "20260324_create_stock_module"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    conn = op.get_bind()

    # Check if users already exist before inserting
    result = conn.execute(sa.text("SELECT username FROM users WHERE username IN ('financeiro', 'estoque')"))
    existing = {row[0] for row in result}

    if "financeiro" not in existing:
        conn.execute(sa.text("""
            INSERT INTO users (username, email, full_name, hashed_password, role, is_active, must_change_password, created_at, updated_at)
            VALUES (:username, :email, :full_name, :hashed_password, :role, :is_active, :must_change_password, :created_at, :updated_at)
        """), {
            "username": "financeiro",
            "email": "financeiro@gasautomation.local",
            "full_name": "Usuário Financeiro",
            "hashed_password": pwd_context.hash("Teste@12345"),
            "role": "financeiro",
            "is_active": True,
            "must_change_password": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

    if "estoque" not in existing:
        conn.execute(sa.text("""
            INSERT INTO users (username, email, full_name, hashed_password, role, is_active, must_change_password, created_at, updated_at)
            VALUES (:username, :email, :full_name, :hashed_password, :role, :is_active, :must_change_password, :created_at, :updated_at)
        """), {
            "username": "estoque",
            "email": "estoque@gasautomation.local",
            "full_name": "Usuário Estoque",
            "hashed_password": pwd_context.hash("Teste@12345"),
            "role": "estoque",
            "is_active": True,
            "must_change_password": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

    # Seed default account "Caixa Principal"
    result = conn.execute(sa.text("SELECT id FROM accounts WHERE name = 'Caixa Principal' LIMIT 1"))
    if result.fetchone() is None:
        conn.execute(sa.text("""
            INSERT INTO accounts (id, name, type, balance, initial_balance, is_active, created_at, updated_at)
            VALUES (:id, :name, :type, :balance, :initial_balance, :is_active, :created_at, :updated_at)
        """), {
            "id": str(uuid.uuid4()),
            "name": "Caixa Principal",
            "type": "caixa",
            "balance": 0.00,
            "initial_balance": 0.00,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

    # Seed stock products P13, P20, P45
    for code, name in [("P13", "Botijão P13 13kg"), ("P20", "Botijão P20 20kg"), ("P45", "Botijão P45 45kg")]:
        result = conn.execute(sa.text("SELECT id FROM stock_products WHERE code = :code"), {"code": code})
        if result.fetchone() is None:
            product_id = str(uuid.uuid4())
            conn.execute(sa.text("""
                INSERT INTO stock_products (id, code, name, unit, cost_price, min_stock_alert, is_active, created_at, updated_at)
                VALUES (:id, :code, :name, :unit, :cost_price, :min_stock_alert, :is_active, :created_at, :updated_at)
            """), {
                "id": product_id,
                "code": code,
                "name": name,
                "unit": "unidade",
                "cost_price": 0.00,
                "min_stock_alert": 10,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            # Create stock balance for this product
            conn.execute(sa.text("""
                INSERT INTO stock_balance (id, stock_product_id, quantity_depot, quantity_in_transit, quantity_with_customers, last_updated, created_at, updated_at)
                VALUES (:id, :stock_product_id, 0, 0, 0, :now, :now, :now)
            """), {
                "id": str(uuid.uuid4()),
                "stock_product_id": product_id,
                "now": datetime.now(timezone.utc),
            })


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE username IN ('financeiro', 'estoque')"))
    conn.execute(sa.text("DELETE FROM stock_balance WHERE stock_product_id IN (SELECT id FROM stock_products WHERE code IN ('P13','P20','P45'))"))
    conn.execute(sa.text("DELETE FROM stock_products WHERE code IN ('P13','P20','P45')"))
    conn.execute(sa.text("DELETE FROM accounts WHERE name = 'Caixa Principal'"))
