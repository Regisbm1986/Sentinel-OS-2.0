from typing import List

def calculate_trend(history: List[dict], key='score'):
    if not history or len(history) < 2:
        return 'stable'
    values = [h[key] for h in history if key in h]
    return 'up' if values[-1] > values[0] else 'down' if values[-1] < values[0] else 'stable'

def calculate_growth(history: List[dict], key='score'):
    if not history or len(history) < 2:
        return 0
    values = [h[key] for h in history if key in h]
    return round(values[-1] - values[0], 2)

def calculate_average(history: List[dict], key='score'):
    values = [h[key] for h in history if key in h]
    return round(sum(values)/len(values),2) if values else 0

def calculate_improvement(history: List[dict], key='score'):
    values = [h[key] for h in history if key in h]
    return max(values) - min(values) if values else 0

def calculate_history_summary(history: List[dict], key='score'):
    return {
        'average': calculate_average(history, key),
        'trend': calculate_trend(history, key),
        'growth': calculate_growth(history, key),
        'improvement': calculate_improvement(history, key)
    }
