import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.auth_models import User
from app.models.driver import Driver, DriverStatus

async def create_test_driver():
    async with AsyncSessionLocal() as session:
        # Check if driver user exists
        result = await session.execute(select(User).where(User.username == "5511999999999"))
        user = result.scalar_one_or_none()
        
        if not user:
            print("Creating test driver user...")
            # Password is 'Teste@123456'
            hashed_password = '$argon2id$v=19$m=65536,t=3,p=4$8p4ghGnVRXPaFVXtYvqR1w$6r4RGzFIUIHdBN5p3DtkKFVNVvQ3H9T1LkWkJB5sI8A'
            user = User(
                username='5511999999999',
                email='motorista@gasautomation.local',
                full_name='Motorista Teste',
                hashed_password=hashed_password,
                role='driver',
                is_active=True,
                must_change_password=False
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print("User created successfully.")

        # Check if driver profile exists
        result = await session.execute(select(Driver).where(Driver.phone == "5511999999999"))
        driver = result.scalar_one_or_none()

        if not driver:
            print("Creating driver profile...")
            driver = Driver(
                name='Motorista Teste',
                phone='5511999999999',
                email='motorista@gasautomation.local',
                vehicle_type='motorcycle',
                is_active=True,
                status=DriverStatus.AVAILABLE.value,
                rating=5.0,
                total_deliveries=0,
            )
            session.add(driver)
            await session.commit()
            print("Driver profile created successfully.")
        else:
            print("Driver profile already exists.")

if __name__ == "__main__":
    asyncio.run(create_test_driver())
