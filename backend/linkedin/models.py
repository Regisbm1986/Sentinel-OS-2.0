# Copied from Sentinel OS backend/linkedin/models.py
from typing import List, Any, Dict

class LinkedInProfile:
    def __init__(self, headline: str, about: str, experience: List[dict], skills: List[str], network: int, visibility: str, ssi: float = None):
        self.headline = headline
        self.about = about
        self.experience = experience
        self.skills = skills
        self.network = network
        self.visibility = visibility
        self.ssi = ssi

    def to_dict(self) -> Dict[str, Any]:
        return {
            'headline': self.headline,
            'about': self.about,
            'experience': self.experience,
            'skills': self.skills,
            'network': self.network,
            'visibility': self.visibility,
            'ssi': self.ssi
        }
