from backend.gpt.client import ask_gpt
from backend.ats.prompts import ATS_PROMPT
from backend.gpt.json_parser import parse_gpt_json


def analyze_resume(resume_text):
    prompt = ATS_PROMPT.format(
        resume=resume_text
    )

    gpt_response = ask_gpt(prompt)
    return parse_gpt_json(gpt_response)
