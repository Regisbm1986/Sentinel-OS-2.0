
import pytest
import sys
if __name__ == "__main__":
    import pytest; raise SystemExit(pytest.main([__file__]))
from products.sentinel_career.backend.payments.plans import get_plans, get_plan
from products.sentinel_career.backend.payments.checkout import create_checkout, confirm_payment
from products.sentinel_career.backend.payments.subscriptions import create_subscription, cancel_subscription, renew_subscription, get_subscription
from products.sentinel_career.backend.payments.models import Plan, Payment, Subscription
from products.sentinel_career.backend.payments.exceptions import PaymentError, SubscriptionError, PlanNotFound, PaymentFailed

def test_get_plans():
    plans = get_plans()
    assert len(plans) == 4
    assert any(p['name'] == 'FREE' for p in plans)
    pro = get_plan('pro')
    assert pro['price'] == 39.90

def test_checkout_confirm():
    payment = create_checkout('u123', 'premium')
    assert payment.plan == 'premium' and payment.status == 'PENDING'
    assert confirm_payment(payment.id)
    with pytest.raises(PaymentFailed):
        confirm_payment('fake-id')

def test_subscriptions():
    sub = create_subscription('u456', 'master')
    assert sub.plan == 'master' and sub.status == 'ACTIVE'
    found = get_subscription(sub.id)
    assert found['id'] == sub.id
    renew_subscription(sub.id)
    cancel_subscription(sub.id)
    with pytest.raises(SubscriptionError):
        renew_subscription('fake-sub-id')
    with pytest.raises(SubscriptionError):
        cancel_subscription('fake-sub-id')
    with pytest.raises(SubscriptionError):
        get_subscription('fake-sub-id')

def test_plan_errors():
    with pytest.raises(PlanNotFound):
        create_checkout('u123', 'invalidplan')
    with pytest.raises(PaymentError):
        from products.sentinel_career.backend.payments.validators import validate_plan_id
        validate_plan_id('invalid')
