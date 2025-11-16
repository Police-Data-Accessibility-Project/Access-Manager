from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any, AsyncGenerator
from typing_extensions import override

from aiohttp import ClientSession, ClientResponseError

from pdap_access_manager.access_manager._base import AccessManagerBase
from pdap_access_manager.enums import RequestType
from pdap_access_manager.exceptions import TokensNotSetError, RequestError
from pdap_access_manager.helpers import authorization_from_token
from pdap_access_manager.models.request import RequestInfo
from pdap_access_manager.models.response import ResponseInfo
from pdap_access_manager.models.tokens import TokensInfo


class AccessManagerAsync(AccessManagerBase):
    """
    Manages login, api key, access and refresh tokens
    """
    @override
    def _expected_session_type(
        self
    ) -> type[ClientSession]:
        return ClientSession

    @override
    def _initialize_session(
        self
    ) -> ClientSession:
        return ClientSession()

    @asynccontextmanager
    async def with_session(self) -> AsyncGenerator["AccessManagerAsync", Any]:
        """Allows just the session lifecycle to be managed."""
        created_session = False
        if self._session is None:
            self._session = self._initialize_session()
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

    @override
    @property
    async def access_token(self) -> str:
        try:
            return self.tokens.access_token
        except TokensNotSetError:
            self._tokens = await self.login()
            return self.tokens.access_token

    @override
    @property
    async def refresh_token(self) -> str:
        try:
            return self.tokens.refresh_token
        except TokensNotSetError:
            self._tokens = await self.login()
            return self.tokens.refresh_token


    @override
    async def load_api_key(self) -> None:
        """Load API key from PDAP:
        """
        url = self._get_api_key_url()
        request_info = RequestInfo(
            type_ = RequestType.POST,
            url=url,
            headers=await self.jwt_header()
        )
        response_info = await self.make_request(request_info)
        self.api_key = response_info.data["api_key"]

    @override
    async def refresh_access_token(self):
        """
        Refresh access and refresh tokens from PDAP
        :return:
        """
        url = self._get_refresh_access_token_url()
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
        except RequestError as e:
            if e.status_code == HTTPStatus.UNAUTHORIZED:  # Token expired, retry logging in
                self._tokens = await self.login()

    @override
    async def make_request(self, ri: RequestInfo, allow_retry: bool = True) -> ResponseInfo:
        """
        Make request to PDAP

        Raises:
            ClientResponseError: If request fails
        """
        try:
            method = self.get_http_method(ri.type_)
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
            raise RequestError(
                message=f"Error making {ri.type_} request to {ri.url}: {e.message}",
                status_code=HTTPStatus(e.status)
            ) from e


    @override
    async def login(self) -> TokensInfo:
        """
        Login to PDAP and retrieve access and refresh tokens

        Raises:
            ClientResponseError: If login fails
        """
        request_info = self.build_login_request_info()
        response_info = await self.make_request(request_info)
        data = response_info.data
        return TokensInfo(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"]
        )



    @override
    async def jwt_header(self) -> dict:
        """
        Retrieve JWT header
        :returns: Dictionary of Bearer Authorization with JWT key
        """
        access_token = await self.access_token
        return authorization_from_token(access_token)

    @override
    async def refresh_jwt_header(self) -> dict:
        """
        Retrieve JWT header

        Returns: Dictionary of Bearer Authorization with JWT key
        """
        refresh_token = await self.refresh_token
        return authorization_from_token(refresh_token)

    @override
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
