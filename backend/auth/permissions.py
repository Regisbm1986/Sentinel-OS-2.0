from products.sentinel_career.backend.auth.models import UserPlan
from products.sentinel_career.backend.auth.exceptions import PermissionDenied

PLANS_PERMISSIONS = {
    'FREE':    {'ATS'},
    'PRO':     {'ATS', 'Career'},
    'PREMIUM': {'ATS', 'Career', 'LinkedIn', 'Jobs'},
    'MASTER':  {'ATS', 'Career', 'LinkedIn', 'Jobs', 'Dashboard', 'Agent'},
    'ADMIN':   {'Admin Panel', 'Payments', 'Users', 'Analytics', 'Logs', 'ATS', 'Career', 'LinkedIn', 'Jobs', 'Dashboard', 'Agent'},
}

def check_permission(plan: str, module: str):
    allowed = PLANS_PERMISSIONS.get(plan, set())
    if module not in allowed:
        raise PermissionDenied(f'Plan {plan} has no access to {module}')
