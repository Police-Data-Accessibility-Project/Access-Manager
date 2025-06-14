from contextlib import asynccontextmanager
from enum import Enum
from http import HTTPStatus
from typing import Optional
from boltons import urlutils

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

class DataSourcesNamespaces(Enum):
    AUTH = "auth"
    LOCATIONS = "locations"
    PERMISSIONS = "permissions"
    SEARCH = "search"
    DATA_SOURCES = "data-sources"
    SOURCE_COLLECTOR = 'source-collector'
    MATCH = "match"
    CHECK = "check"

class SourceCollectorNamespaces(Enum):
    COLLECTORS = "collector"
    SEARCH = "search"
    ANNOTATE = "annotate"

class ResponseInfo(BaseModel):
    status_code: HTTPStatus
    data: Optional[dict]


class RequestInfo(BaseModel):
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

def authorization_from_token(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}"
    }

DEFAULT_DATA_SOURCES_URL = "https://data-sources.pdap.io/api"
DEFAULT_SOURCE_COLLECTOR_URL = "https://source-collector.pdap.io"

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
            data_sources_url: str = DEFAULT_DATA_SOURCES_URL,
            source_collector_url: str = DEFAULT_SOURCE_COLLECTOR_URL
    ):
        self.session = session
        self._external_session = session
        self._access_token = None
        self._refresh_token = None
        self.api_key = api_key
        self.email = email
        self.password = password
        self.data_sources_url = data_sources_url
        self.source_collector_url = source_collector_url

    @asynccontextmanager
    async def with_session(self) -> "AccessManager":
        """Allows just the session lifecycle to be managed."""
        created_session = False
        if self.session is None:
            self.session = ClientSession()
            created_session = True

        try:
            yield self
        finally:
            if created_session:
                await self.session.close()
                self.session = None

    async def __aenter__(self):
        """
        Create session if not already set
        """
        if self.session is None:
            self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Close session
        """
        if self._external_session is None and self.session is not None:
            await self.session.close()

    def build_url(
            self,
            namespace: DataSourcesNamespaces | SourceCollectorNamespaces,
            subdomains: Optional[list[str]] = None,
            base_url: Optional[str] = None
    ) -> str:
        """
        Build url from namespace and subdomains
        :param base_url:
        :param namespace:
        :param subdomains:
        :return:
        """
        if base_url is None:
            base_url = self.data_sources_url
        url = f"{base_url}/{namespace.value}"
        if subdomains is None or len(subdomains) == 0:
            return url
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
            namespace=DataSourcesNamespaces.AUTH,
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
            namespace=DataSourcesNamespaces.AUTH,
            subdomains=["refresh-session"],
        )
        rqi = RequestInfo(
            type_=RequestType.POST,
            url=url,
            headers=await self.refresh_jwt_header()
        )
        try:
            rsi = await self.make_request(rqi, allow_retry=False)
            data = rsi.data
            self._access_token = data['access_token']
            self._refresh_token = data['refresh_token']
        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:  # Token expired, retry logging in
                await self.login(self.email, self.password)

    async def make_request(self, ri: RequestInfo, allow_retry: bool = True) -> ResponseInfo:
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
            if e.status == 401 and allow_retry:  # Unauthorized, token expired?
                print("401 error, refreshing access token...")
                await self.refresh_access_token()
                ri.headers = await self.jwt_header()
                return await self.make_request(ri, allow_retry=False)
            e.message = f"Error making {ri.type_} request to {ri.url}: {e.message}"
            raise e


    async def login(self, email: str, password: str):
        """
        Login to PDAP and retrieve access and refresh tokens
        :param email:
        :param password:
        :return:
        """
        url = self.build_url(
            namespace=DataSourcesNamespaces.AUTH,
            subdomains=["login"]
        )
        request_info = RequestInfo(
            type_=RequestType.POST,
            url=url,
            json_={
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
        return authorization_from_token(access_token)

    async def refresh_jwt_header(self) -> dict:
        """
        Retrieve JWT header
        Returns: Dictionary of Bearer Authorization with JWT key
        """
        refresh_token = await self.refresh_token
        return authorization_from_token(refresh_token)

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
