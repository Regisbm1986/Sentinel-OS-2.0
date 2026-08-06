from pydantic import BaseModel


class NiktoRequest(BaseModel):
    target: str
