plans_data = [
    {"id": "free", "name": "FREE", "price": 0.00, "features": ["ATS"], "active": True},
    {"id": "pro", "name": "PRO", "price": 39.90, "features": ["ATS", "Career"], "active": True},
    {"id": "premium", "name": "PREMIUM", "price": 59.90, "features": ["ATS", "Career", "LinkedIn", "Jobs"], "active": True},
    {"id": "master", "name": "MASTER", "price": 79.90, "features": ["ATS", "Career", "LinkedIn", "Jobs", "Dashboard", "Agent"], "active": True},
]

def get_plans():
    return plans_data

def get_plan(plan_id: str):
    for p in plans_data:
        if p["id"] == plan_id:
            return p
    return None
