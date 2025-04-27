from enum import Enum
from http import HTTPStatus
from typing import Optional

from aiohttp import ClientSession, ClientResponseError
from pydantic import BaseModel


class RequestType(Enum):
    POST = "POST"
    PUT = "PUT"
    GET = "GET"
    DELETE = "DELETE"

request_methods = {
    RequestType.POST: ClientSession.post,
    RequestType.PUT: ClientSession.put,
    RequestType.GET: ClientSession.get,
    RequestType.DELETE: ClientSession.delete,
}

class Namespaces(Enum):
    AUTH = "auth"
    LOCATIONS = "locations"


class CustomHTTPException(Exception):
    pass

class ResponseInfo(BaseModel):
    status_code: HTTPStatus
    data: Optional[dict]


class RequestInfo(BaseModel):
    type_: RequestType
    url: str
    json: Optional[dict] = None
    headers: Optional[dict] = None
    params: Optional[dict] = None
    timeout: Optional[int] = 10

    def kwargs(self) -> dict:
        d = {
            "url": self.url,
        }
        if self.json is not None:
            d['json'] = self.json
        if self.headers is not None:
            d['headers'] = self.headers
        if self.timeout is not None:
            d['timeout'] = self.timeout
        return d



DEFAULT_PDAP_API_URL = "https://data-sources.pdap.io/api"

class AccessManager:
    """
    Manages login, api key, access and refresh tokens
    """
    def __init__(
            self,
            email: str,
            password: str,
            session: Optional[ClientSession] = None,
            api_key: Optional[str] = None,
            api_url: str = DEFAULT_PDAP_API_URL,
    ):
        self.session = session
        self._access_token = None
        self._refresh_token = None
        self.api_key = api_key
        self.email = email
        self.password = password
        self.api_url = api_url

    def build_url(self, namespace: Namespaces, subdomains: Optional[list[str]] = None) -> str:
        """
        Build url from namespace and subdomains
        :param namespace:
        :param subdomains:
        :return:
        """
        url = f"{self.api_url}/{namespace.value}"
        if subdomains is not None:
            url = f"{url}/{'/'.join(subdomains)}"
        return url

    @property
    async def access_token(self) -> str:
        """
        Retrieve access token if not already set
        :return:
        """
        if self._access_token is None:
            await self.login(
                email=self.email,
                password=self.password
            )
        return self._access_token

    @property
    async def refresh_token(self) -> str:
        """
        Retrieve refresh token if not already set
        :return:
        """
        if self._refresh_token is None:
            await self.login(
                email=self.email,
                password=self.password
            )
        return self._refresh_token

    async def load_api_key(self):
        """
        Load API key from PDAP
        :return:
        """
        url = self.build_url(
            namespace=Namespaces.AUTH,
            subdomains=["api-key"]
        )
        request_info = RequestInfo(
            type_ = RequestType.POST,
            url=url,
            headers=await self.jwt_header()
        )
        response_info = await self.make_request(request_info)
        self.api_key = response_info.data["api_key"]

    async def refresh_access_token(self):
        """
        Refresh access and refresh tokens from PDAP
        :return:
        """
        url = self.build_url(
            namespace=Namespaces.AUTH,
            subdomains=["refresh-session"],
        )
        refresh_token = await self.refresh_token
        rqi = RequestInfo(
            type_=RequestType.POST,
            url=url,
            json={"refresh_token": refresh_token},
            headers=await self.jwt_header()
        )
        rsi = await self.make_request(rqi)
        data = rsi.data
        self._access_token = data['access_token']
        self._refresh_token = data['refresh_token']

    async def make_request(self, ri: RequestInfo) -> ResponseInfo:
        """
        Make request to PDAP
        :param ri:
        :return:
        """
        try:
            method = getattr(self.session, ri.type_.value.lower())
            async with method(**ri.kwargs()) as response:
                response.raise_for_status()
                json = await response.json()
                return ResponseInfo(
                    status_code=HTTPStatus(response.status),
                    data=json
                )
        except ClientResponseError as e:
            if e.status == 401:  # Unauthorized, token expired?
                await self.refresh_access_token()
                return await self.make_request(ri)
            else:
                raise CustomHTTPException(f"Error making {ri.type_} request to {ri.url}: {str(e)}")


    async def login(self, email: str, password: str):
        """
        Login to PDAP and retrieve access and refresh tokens
        :param email:
        :param password:
        :return:
        """
        url = self.build_url(
            namespace=Namespaces.AUTH,
            subdomains=["login"]
        )
        request_info = RequestInfo(
            type_=RequestType.POST,
            url=url,
            json={
                "email": email,
                "password": password
            }
        )
        response_info = await self.make_request(request_info)
        data = response_info.data
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]


    async def jwt_header(self) -> dict:
        """
        Retrieve JWT header
        Returns: Dictionary of Bearer Authorization with JWT key
        """
        access_token = await self.access_token
        return {
            "Authorization": f"Bearer {access_token}"
        }

    async def api_key_header(self) -> dict:
        """
        Retrieve API key header
        Returns: Dictionary of Basic Authorization with API key

        """
        if self.api_key is None:
            await self.load_api_key()
        return {
            "Authorization": f"Basic {self.api_key}"
        }
