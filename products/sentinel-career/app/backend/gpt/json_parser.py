import json

def parse_gpt_json(response_text):
    try:
        data = json.loads(response_text)
        return {"success": True, "data": data, "error": None}
    except json.JSONDecodeError as e:
        return {"success": False, "data": None, "error": str(e)}
