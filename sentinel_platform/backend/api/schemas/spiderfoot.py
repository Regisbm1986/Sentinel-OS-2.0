from pydantic import BaseModel


class SpiderFootRequest(BaseModel):
    target: str
