from products.sentinel_career.backend.gpt.client import ask_gpt
from products.sentinel_career.backend.recruiter.prompts import RECRUITER_PROMPT

def analyze_profile(profile_text):

    prompt = RECRUITER_PROMPT.format(
        profile=profile_text
    )

    return ask_gpt(prompt)
