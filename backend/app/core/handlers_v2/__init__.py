"""
Handlers do Flow Engine 2.0
Handlers organizados por fase para os 25 estados.
"""

from .base import BaseHandler, HandlerResult
from .greeting_handlers import GreetingInitialHandler, GreetingReturningHandler
from .identify_handlers import (
    IdentifyTypeHandler,
    IdentifyNamePFHandler,
    IdentifyNamePJHandler,
    IdentifyDocumentCPFHandler,
    IdentifyDocumentCNPJHandler,
    IdentifyUnknownPhoneHandler,
    IdentifyAssociatePhoneHandler,
)
from .ordering_handlers import (
    OrderingProductHandler,
    OrderingQuantityHandler,
    OrderingOperationHandler,
    OrderingMoreItemsHandler,
    OrderingAddressHandler,
    OrderingAddressConfirmHandler,
    OrderingComplementHandler,
    OrderingConfirmRepeatHandler,
)
from .checkout_handlers import (
    CheckoutPaymentHandler,
    CheckoutChangeHandler,
    CheckoutSummaryHandler,
)
from .complete_handlers import (
    CompleteConfirmedHandler,
    CompleteFollowupHandler,
)
from .support_handlers import (
    SupportHumanHandler,
    SupportFAQHandler,
    TrackingStatusHandler,
    TrackingOptionsHandler,
    ErrorRecoveryHandler,
)

__all__ = [
    # Base
    "BaseHandler",
    "HandlerResult",
    
    # Greeting
    "GreetingInitialHandler",
    "GreetingReturningHandler",
    
    # Identify
    "IdentifyTypeHandler",
    "IdentifyNamePFHandler",
    "IdentifyNamePJHandler",
    "IdentifyDocumentCPFHandler",
    "IdentifyDocumentCNPJHandler",
    "IdentifyUnknownPhoneHandler",
    "IdentifyAssociatePhoneHandler",
    
    # Ordering
    "OrderingProductHandler",
    "OrderingQuantityHandler",
    "OrderingOperationHandler",
    "OrderingMoreItemsHandler",
    "OrderingAddressHandler",
    "OrderingAddressConfirmHandler",
    "OrderingComplementHandler",
    "OrderingConfirmRepeatHandler",
    
    # Checkout
    "CheckoutPaymentHandler",
    "CheckoutChangeHandler",
    "CheckoutSummaryHandler",
    
    # Complete
    "CompleteConfirmedHandler",
    "CompleteFollowupHandler",
    
    # Support
    "SupportHumanHandler",
    "SupportFAQHandler",
    "TrackingStatusHandler",
    "TrackingOptionsHandler",
    "ErrorRecoveryHandler",
]
