"""
Career scoring helpers
"""

def weighted_score(scores, weights):
    return sum(scores[k]*weights[k] for k in scores)
