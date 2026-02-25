"""
Core do sistema - Flow Engine e regras de negócio.
"""

from app.core.state_machine import ConversationState, StateTransition
from app.core.flow_engine import flow_engine
from app.core.business_rules import BusinessRules, business_rules

__all__ = [
    "ConversationState",
    "StateTransition",
    "flow_engine",
    "BusinessRules",
    "business_rules",
]
