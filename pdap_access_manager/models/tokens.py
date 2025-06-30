from pydantic import BaseModel


class TokensInfo(BaseModel):
    access_token: str
    refresh_token: str