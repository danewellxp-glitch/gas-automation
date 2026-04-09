from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("No DB URL")
    exit(1)
if database_url.startswith("postgresql+asyncpg"):
    database_url = database_url.replace("postgresql+asyncpg", "postgresql")

engine = create_engine(database_url)
inspector = inspect(engine)
columns = inspector.get_columns("customers")
for c in columns:
    print(c["name"])
