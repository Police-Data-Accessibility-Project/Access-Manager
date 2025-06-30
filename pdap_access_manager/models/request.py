from typing import Optional

from boltons import urlutils
from pydantic import BaseModel

from pdap_access_manager.enums import RequestType


class RequestInfo(BaseModel):
    """Information about a given request

    Attributes:
        type_: RequestType: The type of HTTP request
        url: str: The url to send the request to
        json_: Optional[dict] = None: Any json data to include in the request
        headers: Optional[dict] = None: Any headers to include in the request
        params: Optional[dict] = None: Any query parameters to include in the request
        timeout: Optional[int] = 10: The timeout for the request

    """


    type_: RequestType
    url: str
    json_: Optional[dict] = None
    headers: Optional[dict] = None
    params: Optional[dict] = None
    timeout: Optional[int] = 10

    def kwargs(self) -> dict:
        d = {
            "url": self.url_with_query_params(),
        }
        if self.json_ is not None:
            d['json'] = self.json_
        if self.headers is not None:
            d['headers'] = self.headers
        if self.timeout is not None:
            d['timeout'] = self.timeout
        return d

    def url_with_query_params(self) -> str:
        if self.params is None:
            return self.url
        url = urlutils.URL(self.url)
        url.query_params.update(self.params)
        return url.to_text()
