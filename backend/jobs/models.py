from typing import List, Dict, Any

class JobMatch:
    def __init__(self, title: str, compatibility: int, salary: int, estimated_interview: int, missing_skills: List[str], reason: str):
        self.title = title
        self.compatibility = compatibility
        self.salary = salary
        self.estimated_interview = estimated_interview
        self.missing_skills = missing_skills
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "compatibility": self.compatibility,
            "salary": self.salary,
            "estimated_interview": self.estimated_interview,
            "missing_skills": self.missing_skills,
            "reason": self.reason
        }
