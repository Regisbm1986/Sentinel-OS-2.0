class PaymentError(Exception):
    pass
class PlanNotFound(PaymentError):
    pass
class PaymentFailed(PaymentError):
    pass
class SubscriptionError(PaymentError):
    pass
class StorageError(PaymentError):
    pass
