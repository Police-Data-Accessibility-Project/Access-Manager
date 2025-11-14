from contextlib import contextmanager
from http import HTTPStatus
from typing import Generator, Any
from typing_extensions import override

from requests import Session, HTTPError

from pdap_access_manager.access_manager._base import AccessManagerBase
from pdap_access_manager.enums import RequestType
from pdap_access_manager.exceptions import TokensNotSetError, RequestError
from pdap_access_manager.helpers import authorization_from_token
from pdap_access_manager.models.request import RequestInfo
from pdap_access_manager.models.response import ResponseInfo
from pdap_access_manager.models.tokens import TokensInfo


class AccessManagerSync(AccessManagerBase):

    @override
    def _initialize_session(self) -> Session:
        return Session()

    @override
    @property
    def access_token(self) -> str:
        try:
            return self.tokens.access_token
        except TokensNotSetError:
            self._tokens = self.login()
            return self.tokens.access_token

    @override
    @property
    def refresh_token(self) -> str:
        try:
            return self.tokens.refresh_token
        except TokensNotSetError:
            self._tokens = self.login()
            return self.tokens.refresh_token

    @override
    def load_api_key(self) -> None:
        url = self._get_api_key_url()
        request_info = RequestInfo(
            type_=RequestType.POST,
            url=url,
            headers=self.jwt_header()
        )
        response_info = self.make_request(request_info)
        self.api_key = response_info.data["api_key"]

    @override
    def refresh_access_token(self) -> None:
        url = self._get_refresh_access_token_url()
        rqi = RequestInfo(
            type_=RequestType.POST,
            url=url,
            headers=self.refresh_jwt_header()
        )
        try:
            rsi = self.make_request(rqi, allow_retry=False)
            data = rsi.data
            self._tokens = TokensInfo(
                access_token=data['access_token'],
                refresh_token=data['refresh_token']
            )
        except RequestError as e:
            if e.status_code == HTTPStatus.UNAUTHORIZED:  # Token expired, retry logging in
                self._tokens = self.login()

    @override
    def make_request(self, ri: RequestInfo, allow_retry: bool = True) -> ResponseInfo:
        try:
            method = self.get_http_method(ri.type_)
            response = method(**ri.kwargs())
            response.raise_for_status()
            json = response.json()
            return ResponseInfo(
                status_code=HTTPStatus(response.status),
                data=json
            )
        except HTTPError as e:
            status_code = e.response.status_code
            if status_code != HTTPStatus.UNAUTHORIZED or not allow_retry:
                raise RequestError(
                    message=f"Error making {ri.type_} request to {ri.url}",
                    status_code=HTTPStatus(status_code)
                ) from e
            print("401 error, refreshing access token...")
            self.refresh_access_token()
            ri.headers = self.jwt_header()
            return self.make_request(ri, allow_retry=False)


    @override
    def login(self) -> TokensInfo:
        request_info = self.build_login_request_info()
        response_info = self.make_request(request_info)
        data = response_info.data
        return TokensInfo(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"]
        )

    @override
    def jwt_header(self) -> dict:
        """
        Retrieve JWT header
        :returns: Dictionary of Bearer Authorization with JWT key
        """
        access_token = self.access_token
        return authorization_from_token(access_token)

    @override
    def refresh_jwt_header(self) -> dict:
        """
        Retrieve JWT header

        Returns: Dictionary of Bearer Authorization with JWT key
        """
        refresh_token = self.refresh_token
        return authorization_from_token(refresh_token)

    @override
    def api_key_header(self) -> dict:
        """
        Retrieve API key header
        Returns: Dictionary of Basic Authorization with API key

        """
        if self.api_key is None:
            self.load_api_key()
        return {
            "Authorization": f"Basic {self.api_key}"
        }

    @override
    def _expected_session_type(
        self
    ) -> type[Session]:
        return Session

    @contextmanager
    def with_session(self) -> Generator["AccessManagerSync", Any, Any]:
        """Allows just the session lifecycle to be managed."""
        created_session = False
        if self._session is None:
            self._session = self._initialize_session()
            created_session = True

        try:
            yield self
        finally:
            if created_session:
                self._session.close()
                self._session = None

    def __enter__(self):
        """
        Create session if not already set
        """
        if self._session is None:
            self._session = self._initialize_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close session
        """
        if self._external_session is None and self._session is not None:
            self._session.close()