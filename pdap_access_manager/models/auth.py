from pydantic import BaseModel


class AuthInfo(BaseModel):
    email: str
    password: str