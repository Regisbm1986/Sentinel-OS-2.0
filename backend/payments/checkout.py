import uuid

from products.sentinel_career.backend.payments.models import Payment
from products.sentinel_career.backend.payments.storage import JSONStorage
from products.sentinel_career.backend.payments.plans import get_plan
from products.sentinel_career.backend.payments.exceptions import PaymentFailed, PlanNotFound

storage = JSONStorage("payments.json")

# Simplificado: simula criação de pagamento/checkout

def create_checkout(user_id: str, plan_id: str):
    plan = get_plan(plan_id)
    if not plan:
        raise PlanNotFound("Plano não existe")
    payment = Payment(str(uuid.uuid4()), user_id, plan_id, plan["price"], "PENDING")
    storage.save(payment.to_dict())
    return payment

def confirm_payment(payment_id: str):
    data = storage.load_all()
    found = False
    for payment in data:
        if payment["id"] == payment_id and payment["status"] == "PENDING":
            payment["status"] = "CONFIRMED"
            found = True
    if not found:
        raise PaymentFailed("Pagamento não encontrado ou já confirmado")
    storage.overwrite(data)
    return True
