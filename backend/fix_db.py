import sys
import os

try:
    from sqlalchemy import create_engine, text
    print("Found sqlalchemy")
    db_url = "postgresql://gasadmin:gasadmin123@localhost:5433/gas_automation"
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_order_data JSONB;"))
        conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferences JSONB;"))
        conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS order_count INTEGER DEFAULT 0;"))
        conn.commit()
    print("Columns added successfully via sqlalchemy")
except Exception as e:
    print(f"Failed via sqlalchemy: {e}")
    try:
        import psycopg2
        print("Found psycopg2")
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            user="gasadmin",
            password="gasadmin123",
            dbname="gas_automation"
        )
        cur = conn.cursor()
        cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_order_data JSONB;")
        cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferences JSONB;")
        cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS order_count INTEGER DEFAULT 0;")
        conn.commit()
        cur.close()
        conn.close()
        print("Columns added successfully via psycopg2")
    except Exception as e2:
        print(f"Failed via psycopg2: {e2}")

