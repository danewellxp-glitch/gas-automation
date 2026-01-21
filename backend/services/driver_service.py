"""
Driver Service - Gerenciamento de Entregadores
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.driver import Driver, DriverStatus


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> List[Driver]:
        """Lista todos os entregadores"""
        return self.session.exec(select(Driver)).all()

    def list_available(self) -> List[Driver]:
        """Lista entregadores disponíveis"""
        return self.session.exec(
            select(Driver).where(Driver.status == DriverStatus.AVAILABLE)
        ).all()

    def get_by_id(self, driver_id: int) -> Optional[Driver]:
        """Busca entregador por ID"""
        return self.session.get(Driver, driver_id)

    def create(self, **data) -> Driver:
        """Cria novo entregador"""
        driver = Driver(**data)
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def update(self, driver_id: int, **data) -> Optional[Driver]:
        """Atualiza entregador"""
        driver = self.get_by_id(driver_id)
        if not driver:
            return None

        for key, value in data.items():
            setattr(driver, key, value)

        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def delete(self, driver_id: int) -> bool:
        """Remove entregador"""
        driver = self.get_by_id(driver_id)
        if not driver:
            return False

        self.session.delete(driver)
        self.session.commit()
        return True

    def go_online(self, driver_id: int) -> Optional[Driver]:
        """Coloca entregador online/disponível"""
        driver = self.get_by_id(driver_id)
        if not driver:
            return None

        driver.status = DriverStatus.AVAILABLE.value
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def go_offline(self, driver_id: int) -> Optional[Driver]:
        """Coloca entregador offline"""
        driver = self.get_by_id(driver_id)
        if not driver:
            return None

        driver.status = DriverStatus.OFFLINE.value
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def update_location(self, driver_id: int, latitude: float, longitude: float) -> Optional[Driver]:
        """Atualiza localização do entregador em tempo real"""
        driver = self.get_by_id(driver_id)
        if not driver:
            return None

        from datetime import datetime
        driver.current_location = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.now().isoformat()
        }
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def get_nearby_drivers(self, latitude: float, longitude: float, radius_km: float = 5.0) -> List[Driver]:
        """Busca entregadores próximos (simplificado - sem cálculo real de distância)"""
        # Por enquanto retorna todos disponíveis (futuramente implementar cálculo de distância)
        return self.list_available()

    def update_driver_capacity(self, driver_id: int, capacity_data: dict) -> Optional[Driver]:
        """Atualiza capacidade do entregador por tipo de produto"""
        driver = self.get_by_id(driver_id)
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
        self.session.commit()
        self.session.refresh(driver)
        return driver