import logging
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Optional, Any, AsyncGenerator

from aiohttp import ClientSession, ClientResponseError

from pdap_access_manager.constants import DEFAULT_DATA_SOURCES_URL, DEFAULT_SOURCE_COLLECTOR_URL
from pdap_access_manager.enums import RequestType, DataSourcesNamespaces, SourceCollectorNamespaces
from pdap_access_manager.exceptions import TokensNotSetError, AuthNotSetError
from pdap_access_manager.models.auth import AuthInfo
from pdap_access_manager.models.request import RequestInfo
from pdap_access_manager.models.response import ResponseInfo
from pdap_access_manager.models.tokens import TokensInfo

request_methods = {
    RequestType.POST: ClientSession.post,
    RequestType.PUT: ClientSession.put,
    RequestType.GET: ClientSession.get,
    RequestType.DELETE: ClientSession.delete,
}


def authorization_from_token(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}"
    }


class AccessManager:
    """
    Manages login, api key, access and refresh tokens
    """
    def __init__(
            self,
            auth: Optional[AuthInfo] = None,
            tokens: Optional[TokensInfo] = None,
            session: Optional[ClientSession] = None,
            api_key: Optional[str] = None,
            data_sources_url: str = DEFAULT_DATA_SOURCES_URL,
            source_collector_url: str = DEFAULT_SOURCE_COLLECTOR_URL
    ):
        self._session = session
        self._external_session = session
        self._tokens = tokens
        self._auth = auth
        self.api_key = api_key
        self.data_sources_url = data_sources_url
        self.source_collector_url = source_collector_url
        self.logger = logging.getLogger(__name__)

    @property
    def auth(self) -> AuthInfo:
        if self._auth is None:
            raise AuthNotSetError
        return self._auth

    @property
    def tokens(self) -> TokensInfo:
        if self._tokens is None:
            raise TokensNotSetError
        return self._tokens

    @property
    def session(self) -> ClientSession:
        if self._external_session is not None:
            return self._external_session
        if self._session is not None:
            return self._session
        self.logger.warning(
            "No ClientSession set, creating a new ClientSession. "
            "Please use the `with_session` context manager if possible or otherwise "
            "pass in a ClientSession to the constructor."
        )
        self._session = ClientSession()
        return self._session



    @asynccontextmanager
    async def with_session(self) -> AsyncGenerator["AccessManager", Any]:
        """Allows just the session lifecycle to be managed."""
        created_session = False
        if self._session is None:
            self._session = ClientSession()
            created_session = True

        try:
            yield self
        finally:
            if created_session:
                await self._session.close()
                self._session = None

    async def __aenter__(self):
        """
        Create session if not already set
        """
        if self._session is None:
            self._session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Close session
        """
        if self._external_session is None and self._session is not None:
            await self._session.close()

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
        try:
            return self.tokens.access_token
        except TokensNotSetError:
            self._tokens = await self.login()
            return self.tokens.access_token

    @property
    async def refresh_token(self) -> str:
        """
        Retrieve refresh token if not already set
        :return:
        """
        try:
            return self.tokens.refresh_token
        except TokensNotSetError:
            self._tokens = await self.login()
            return self.tokens.refresh_token


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
            self._tokens = TokensInfo(
                access_token=data['access_token'],
                refresh_token=data['refresh_token']
            )
        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:  # Token expired, retry logging in
                self._tokens = await self.login()

    async def make_request(self, ri: RequestInfo, allow_retry: bool = True) -> ResponseInfo:
        """
        Make request to PDAP

        Raises:
            ClientResponseError: If request fails
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


    async def login(self) -> TokensInfo:
        """
        Login to PDAP and retrieve access and refresh tokens

        Raises:
            ClientResponseError: If login fails
        """
        url = self.build_url(
            namespace=DataSourcesNamespaces.AUTH,
            subdomains=["login"]
        )
        auth = self.auth
        request_info = RequestInfo(
            type_=RequestType.POST,
            url=url,
            json_={
                "email": auth.email,
                "password": auth.password
            }
        )
        response_info = await self.make_request(request_info)
        data = response_info.data
        return TokensInfo(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"]
        )



    async def jwt_header(self) -> dict:
        """
        Retrieve JWT header
        :returns: Dictionary of Bearer Authorization with JWT key
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
