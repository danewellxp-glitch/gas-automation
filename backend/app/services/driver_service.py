"""
Driver Service - Gerenciamento de Entregadores
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver import Driver, DriverStatus


class DriverService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> List[Driver]:
        """Lista todos os entregadores"""
        result = await self.session.execute(select(Driver))
        return result.scalars().all()

    async def list_available(self) -> List[Driver]:
        """Lista entregadores disponíveis"""
        result = await self.session.execute(
            select(Driver).where(Driver.status == DriverStatus.AVAILABLE)
        )
        return result.scalars().all()

    async def get_by_id(self, driver_id: int) -> Optional[Driver]:
        """Busca entregador por ID"""
        return await self.session.get(Driver, driver_id)

    async def create(self, **data) -> Driver:
        """Cria novo entregador"""
        driver = Driver(**data)
        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver

    async def update(self, driver_id: int, **data) -> Optional[Driver]:
        """Atualiza entregador"""
        driver = await self.get_by_id(driver_id)
        if not driver:
            return None

        for key, value in data.items():
            setattr(driver, key, value)

        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver

    async def delete(self, driver_id: int) -> bool:
        """Remove entregador"""
        driver = await self.get_by_id(driver_id)
        if not driver:
            return False

        await self.session.delete(driver)
        await self.session.commit()
        return True

    async def go_online(self, driver_id: int) -> Optional[Driver]:
        """Coloca entregador online/disponível"""
        driver = await self.get_by_id(driver_id)
        if not driver:
            return None

        driver.status = DriverStatus.AVAILABLE.value
        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver

    async def go_offline(self, driver_id: int) -> Optional[Driver]:
        """Coloca entregador offline"""
        driver = await self.get_by_id(driver_id)
        if not driver:
            return None

        driver.status = DriverStatus.OFFLINE.value
        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver

    async def update_location(self, driver_id: int, latitude: float, longitude: float) -> Optional[Driver]:
        """Atualiza localização do entregador em tempo real"""
        driver = await self.get_by_id(driver_id)
        if not driver:
            return None

        from datetime import datetime
        driver.current_location = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.now().isoformat()
        }
        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver

    async def get_nearby_drivers(self, latitude: float, longitude: float, radius_km: float = 5.0) -> List[Driver]:
        """Busca entregadores próximos (simplificado - sem cálculo real de distância)"""
        # Por enquanto retorna todos disponíveis (futuramente implementar cálculo de distância)
        return await self.list_available()

    async def update_driver_capacity(self, driver_id: int, capacity_data: dict) -> Optional[Driver]:
        """Atualiza capacidade do entregador por tipo de produto"""
        driver = await self.get_by_id(driver_id)
        if not driver:
            return None

        # Adiciona campos de capacidade se não existirem
        if hasattr(driver, 'capacity_p13') or not hasattr(driver, 'capacity_p13'):
            # Se o modelo não tiver esses campos, apenas retorna
            return driver

        for key, value in capacity_data.items():
            if hasattr(driver, key):
                setattr(driver, key, value)

        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver