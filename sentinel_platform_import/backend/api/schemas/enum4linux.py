from pydantic import BaseModel


class Enum4LinuxRequest(BaseModel):
    target: str
