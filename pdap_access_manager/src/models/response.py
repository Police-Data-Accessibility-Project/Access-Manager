from http import HTTPStatus
from typing import Optional

from pydantic import BaseModel


class ResponseInfo(BaseModel):
    status_code: HTTPStatus
    data: Optional[dict]
