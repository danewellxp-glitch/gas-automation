"""
Schemas Pydantic para Driver (Entregador).
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class DriverBase(BaseModel):
    """Schema base para Driver."""
    name: str = Field(..., min_length=3, max_length=100, description="Nome completo do entregador")
    phone: str = Field(..., min_length=10, max_length=20, description="Telefone para contato")
    email: Optional[str] = Field(None, max_length=100, description="Email opcional")
    vehicle_type: Optional[str] = Field(None, max_length=50, description="Tipo de veículo (moto, carro)")
    license_plate: Optional[str] = Field(None, max_length=10, description="Placa do veículo")
    bairro: Optional[str] = Field(None, max_length=100, description="Bairro de atuação")


class DriverCreate(DriverBase):
    """Schema para criar novo entregador."""
    pass


class DriverUpdate(BaseModel):
    """Schema para atualizar entregador (todos os campos opcionais)."""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    vehicle_type: Optional[str] = Field(None, max_length=50)
    license_plate: Optional[str] = Field(None, max_length=10)
    bairro: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class DriverStatusUpdate(BaseModel):
    """Schema para atualizar status do entregador."""
    status: str = Field(..., description="Status: offline, available, busy, break")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['offline', 'available', 'busy', 'break']
        if v not in valid_statuses:
            raise ValueError(f"Status deve ser um de: {', '.join(valid_statuses)}")
        return v


class DriverLocationUpdate(BaseModel):
    """Schema para atualizar localização do entregador."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude GPS")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude GPS")


class DriverPushTokenUpdate(BaseModel):
    """Schema para registrar token FCM de push notification."""
    push_token: str = Field(..., min_length=10, max_length=255, description="FCM device token")


class DriverResponse(DriverBase):
    """Schema de resposta com todos os dados do entregador."""
    id: UUID
    status: str
    current_location: Optional[dict] = None
    rating: float
    total_deliveries: int
    is_active: bool
    last_online: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DriverBrief(BaseModel):
    """Schema resumido do entregador (para listagens)."""
    id: UUID
    name: str
    phone: str
    status: str
    vehicle_type: Optional[str] = None
    bairro: Optional[str] = None
    rating: float
    total_deliveries: int
    is_active: bool

    class Config:
        from_attributes = True


class DriverStats(BaseModel):
    """Schema de estatísticas do entregador."""
    driver_id: UUID
    driver_name: str
    total_deliveries: int
    today_deliveries: int
    week_deliveries: int
    month_deliveries: int
    rating: float
    average_delivery_time_minutes: Optional[float] = None
    success_rate: float
    status: str


class DeliveryProblemReport(BaseModel):
    """Schema para reportar problema na entrega."""
    problem_type: str = Field(..., description="Tipo: customer_absent, wrong_address, product_issue, other")
    description: str = Field(..., min_length=10, max_length=500, description="Descrição do problema")
    
    @validator('problem_type')
    def validate_problem_type(cls, v):
        valid_types = ['customer_absent', 'wrong_address', 'product_issue', 'payment_issue', 'other']
        if v not in valid_types:
            raise ValueError(f"Tipo deve ser um de: {', '.join(valid_types)}")
        return v


class DeliveryStatusUpdate(BaseModel):
    """Schema para atualizar status da entrega."""
    status: str = Field(..., description="Status: picked_up, in_transit, arrived, delivered")
    notes: Optional[str] = Field(None, max_length=500, description="Observações opcionais")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['picked_up', 'in_transit', 'arrived', 'delivered']
        if v not in valid_statuses:
            raise ValueError(f"Status deve ser um de: {', '.join(valid_statuses)}")
        return v


# ==================== SCHEMAS DE TEMPO TRABALHADO ====================

class DriverTimeSummary(BaseModel):
    """Resumo de tempo trabalhado do driver."""
    driver_id: str
    driver_name: Optional[str] = None
    current_status: Optional[str] = None
    rating: Optional[float] = None
    period: Dict[str, str]
    by_status: Dict[str, Dict]
    total_minutes: int
    total_hours: float


class DailyRankingItem(BaseModel):
    """Item do ranking diário."""
    position: int
    driver_id: str
    driver_name: str
    rating: float
    vehicle_type: Optional[str] = None
    deliveries_count: int


class DriversMetricsDashboard(BaseModel):
    """Dashboard completo de métricas dos drivers."""
    summary: Dict[str, Any]
    ranking: List[DailyRankingItem]
    drivers_time: List[DriverTimeSummary]
