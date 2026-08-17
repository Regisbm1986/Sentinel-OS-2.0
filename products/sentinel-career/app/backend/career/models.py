"""
Career Health Models
"""
from typing import Dict, Any

class CareerHealthResult:
    def __init__(self, career_health, status, color, scores, strengths, priorities):
        self.career_health = career_health
        self.status = status
        self.color = color
        self.scores = scores
        self.strengths = strengths
        self.priorities = priorities

    def to_json(self) -> Dict[str, Any]:
        return {
            "career_health": self.career_health,
            "status": self.status,
            "color": self.color,
            "scores": self.scores,
            "strengths": self.strengths,
            "priorities": self.priorities
        }
