import asyncio
from sqlmodel import Session, select
from app.database import engine
from app.models.auth_models import User
from app.auth import get_password_hash

async def create_test_user():
    """Cria usuário de teste no banco de dados"""
    
    # Dados do usuário teste
    test_user = User(
        username="admin",
        email="admin@gasautomation.local",
        full_name="Admin Test",
        hashed_password=get_password_hash("Admin@123456"),
        role="admin",
        is_active=True
    )
    
    # Criar sessão e adicionar usuário
    with Session(engine) as session:
        # Verificar se o usuário já existe
        existing = session.exec(
            select(User).where(User.email == "admin@gasautomation.local")
        ).first()
        
        if existing:
            print("✅ Usuário admin@gasautomation.local já existe!")
            return
        
        session.add(test_user)
        session.commit()
        print("✅ Usuário admin@gasautomation.local criado com sucesso!")
        print(f"   Email: admin@gasautomation.local")
        print(f"   Senha: Admin@123456")
        print(f"   Role: admin")

if __name__ == "__main__":
    asyncio.run(create_test_user())
