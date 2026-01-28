"""
Admin Debug Tools (admin-only + confirmação dupla)

⚠️ Endpoints perigosos exigem:
- confirm_token válido (emitido em /api/admin/debug/confirm)
- confirm_text == "CONFIRM"
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth import get_current_user
from app.core.flow_engine import flow_engine
from app.core.state_machine import ConversationState, StateTransition
from app.database import get_db, redis_manager
from app.models.auth_models import AuditLog, User
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product

router = APIRouter(prefix="/admin/debug", tags=["Admin", "Debug"])


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this resource")


async def _write_audit_log(
    session: AsyncSession,
    *,
    action: str,
    actor_user_id: Optional[int],
    details: Optional[str] = None,
) -> None:
    audit = AuditLog(
        action=action,
        user_id=actor_user_id,
        details=details,
        timestamp=datetime.utcnow(),
    )
    session.add(audit)
    await session.commit()


class ConfirmResponse(BaseModel):
    confirm_token: str
    expires_in_seconds: int


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_dangerous_action(
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    token = secrets.token_urlsafe(16)
    key = f"admin_confirm:{token}"
    ttl = 300  # 5 min
    await redis_manager.client.set(key, str(current_user.id), ex=ttl)
    return {"confirm_token": token, "expires_in_seconds": ttl}


async def _require_confirm(token: str, confirm_text: str, *, current_user: User) -> None:
    if confirm_text != "CONFIRM":
        raise HTTPException(status_code=400, detail='confirm_text must be "CONFIRM"')
    key = f"admin_confirm:{token}"
    owner = await redis_manager.client.get(key)
    if not owner or str(current_user.id) != str(owner):
        raise HTTPException(status_code=403, detail="Invalid or expired confirm_token")


class SimulateMessageRequest(BaseModel):
    phone: str
    message: str
    message_id: Optional[str] = None
    confirm_token: str
    confirm_text: str


@router.post("/simulate-message")
async def simulate_message_admin(
    body: SimulateMessageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    await _require_confirm(body.confirm_token, body.confirm_text, current_user=current_user)

    context_before = await flow_engine.get_context(body.phone)
    current_state = context_before.state.value

    result = await flow_engine.process_message(phone=body.phone, message=body.message, message_id=body.message_id)

    responses = [
        {
            "text": r.text,
            "buttons": r.buttons,
            "image_url": r.image_url,
            "footer": r.footer,
        }
        for r in result.responses
    ]

    await _write_audit_log(
        session,
        action="DEBUG_SIMULATE_MESSAGE",
        actor_user_id=current_user.id,
        details=f"phone={body.phone} current_state={current_state} new_state={result.new_state.value}",
    )

    return {
        "success": result.success,
        "current_state": current_state,
        "new_state": result.new_state.value,
        "responses": responses,
        "context": result.context.to_dict(),
        "error": result.error,
    }


@router.get("/context/{phone}")
async def get_context_admin(
    phone: str,
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    context = await flow_engine.get_context(phone)
    return {"phone": phone, "context": context.to_dict()}


class ResetContextRequest(BaseModel):
    confirm_token: str
    confirm_text: str


@router.delete("/context/{phone}")
async def reset_context_admin(
    phone: str,
    body: ResetContextRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    await _require_confirm(body.confirm_token, body.confirm_text, current_user=current_user)
    await redis_manager.delete_conversation_state(phone)
    await _write_audit_log(session, action="DEBUG_RESET_CONTEXT", actor_user_id=current_user.id, details=f"phone={phone}")
    return {"phone": phone, "message": "Contexto resetado com sucesso"}


@router.get("/flow-states")
async def list_flow_states_admin(
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    states: dict[str, Any] = {}
    for st in ConversationState:
        transitions = StateTransition.get_valid_transitions(st)
        states[st.value] = {"name": st.name, "valid_transitions": [t.value for t in transitions]}
    return {"states": states}


@router.get("/redis/info")
async def redis_info(
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    info_memory = await redis_manager.client.info(section="memory")
    info_clients = await redis_manager.client.info(section="clients")
    info_stats = await redis_manager.client.info(section="stats")
    return {"memory": info_memory, "clients": info_clients, "stats": info_stats}


@router.get("/redis/inspect")
async def redis_inspect(
    pattern: str = Query("chat:*"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    allowed_prefixes = ("chat:", "order_lock:", "rate:", "admin_confirm:")
    if not any(pattern.startswith(p) for p in allowed_prefixes):
        raise HTTPException(status_code=400, detail="Pattern not allowed")

    keys = []
    async for k in redis_manager.client.scan_iter(match=pattern, count=200):
        keys.append(k)
        if len(keys) >= limit:
            break

    values: dict[str, Any] = {}
    for k in keys:
        values[k] = await redis_manager.client.get(k)

    return {"pattern": pattern, "count": len(keys), "items": values}


class CreateFakeOrderRequest(BaseModel):
    phone: str = Field(..., description="Telefone do cliente (será criado se não existir)")
    product_code: str = Field("P13")
    quantity: int = Field(1, ge=1, le=20)
    confirm_token: str
    confirm_text: str


@router.post("/create-fake-order")
async def create_fake_order(
    body: CreateFakeOrderRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    await _require_confirm(body.confirm_token, body.confirm_text, current_user=current_user)

    # product
    prod_res = await session.execute(select(Product).where(Product.code == body.product_code))
    product = prod_res.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=400, detail="Product not found. Create/sync products first.")

    # customer (create if missing)
    cust_res = await session.execute(select(Customer).where(Customer.phone == body.phone))
    customer = cust_res.scalar_one_or_none()
    if not customer:
        customer = Customer(phone=body.phone, name="Cliente Fake", address={"bairro": "Boqueirão"})
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

    qty = int(body.quantity)
    unit_price = Decimal(str(product.price))
    subtotal = unit_price * Decimal(qty)

    order = Order(
        customer_id=customer.id,
        status=OrderStatus.PENDING.value,
        payment_method="pix",
        total_amount=subtotal,
        delivery_address=customer.address,
        delivery_bairro=(customer.address or {}).get("bairro") if customer.address else None,
        notes="FAKE ORDER (admin debug)",
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_code=product.code,
        product_name=product.name,
        quantity=qty,
        unit_price=unit_price,
        subtotal=subtotal,
    )
    session.add(item)
    await session.commit()

    await _write_audit_log(
        session,
        action="DEBUG_CREATE_FAKE_ORDER",
        actor_user_id=current_user.id,
        details=f"order_id={order.id} phone={body.phone} product={product.code} qty={qty}",
    )

    return {"order_id": str(order.id), "order_number": order.order_number, "status": order.status, "total_amount": str(order.total_amount)}


class ReexecuteStateMachineRequest(BaseModel):
    phone: str
    messages: list[str] = Field(..., min_length=1, max_length=30)
    confirm_token: str
    confirm_text: str


@router.post("/reexecute-state-machine")
async def reexecute_state_machine(
    body: ReexecuteStateMachineRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    await _require_confirm(body.confirm_token, body.confirm_text, current_user=current_user)

    steps = []
    for msg in body.messages:
        before = await flow_engine.get_context(body.phone)
        res = await flow_engine.process_message(phone=body.phone, message=msg)
        steps.append(
            {
                "message": msg,
                "from_state": before.state.value,
                "to_state": res.new_state.value,
                "success": res.success,
                "error": res.error,
                "responses": [{"text": r.text, "buttons": r.buttons} for r in res.responses],
            }
        )

    final_ctx = await flow_engine.get_context(body.phone)

    await _write_audit_log(
        session,
        action="DEBUG_REEXECUTE_STATE_MACHINE",
        actor_user_id=current_user.id,
        details=f"phone={body.phone} steps={len(steps)}",
    )

    return {"phone": body.phone, "steps": steps, "final_context": final_ctx.to_dict()}


class RaiseErrorRequest(BaseModel):
    message: str = Field("Debug forced error")
    confirm_token: str
    confirm_text: str


@router.post("/raise-error")
async def raise_error_for_testing(
    body: RaiseErrorRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint controlado para forçar um erro 500 e validar a Central de Erros.
    Admin-only + confirmação dupla.
    """
    _require_admin(current_user)
    await _require_confirm(body.confirm_token, body.confirm_text, current_user=current_user)
    await _write_audit_log(session, action="DEBUG_RAISE_ERROR", actor_user_id=current_user.id, details=body.message)
    raise RuntimeError(body.message)

