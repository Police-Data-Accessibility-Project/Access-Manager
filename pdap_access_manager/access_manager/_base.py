import logging
from abc import ABC, abstractmethod, abstractproperty
from typing import Optional

from aiohttp import ClientSession

from pdap_access_manager.constants import DEFAULT_DATA_SOURCES_URL, DEFAULT_SOURCE_COLLECTOR_URL
from pdap_access_manager.enums import DataSourcesNamespaces, SourceCollectorNamespaces, RequestType
from pdap_access_manager.exceptions import AuthNotSetError, TokensNotSetError, IncorrectSessionError
from pdap_access_manager.models.auth import AuthInfo
from pdap_access_manager.models.request import RequestInfo
from pdap_access_manager.models.response import ResponseInfo
from pdap_access_manager.models.tokens import TokensInfo
from requests import Session


class AccessManagerBase(ABC):

    def __init__(
            self,
            auth: Optional[AuthInfo] = None,
            tokens: Optional[TokensInfo] = None,
            session: Optional[ClientSession | Session] = None,
            api_key: Optional[str] = None,
            data_sources_url: str = DEFAULT_DATA_SOURCES_URL,
            source_collector_url: str = DEFAULT_SOURCE_COLLECTOR_URL
    ):
        self._validate_session(session)
        self._session = session
        self._external_session = session
        self._tokens = tokens
        self._auth = auth
        self.api_key = api_key
        self.data_sources_url = data_sources_url
        self.source_collector_url = source_collector_url
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def _expected_session_type(
        self
    ) -> type[ClientSession | Session]:
        raise NotImplementedError

    def _validate_session(
        self,
        session: ClientSession | Session | None
    ):
        """Validates that the expected session type is set."""
        if session is None:
            return
        expected_session_type = self._expected_session_type()
        if not isinstance(session, expected_session_type):
            raise IncorrectSessionError(
                f"Expected session type: {expected_session_type.__name__}, "
                f"got: {type(session).__name__}"
            )

    @abstractmethod
    def _initialize_session(
        self
    ) -> ClientSession | Session:
        raise NotImplementedError

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
    def session(self) -> ClientSession | Session:
        if self._external_session is not None:
            return self._external_session
        if self._session is not None:
            return self._session
        self.logger.warning(
            "No Session set, creating a new Session. "
            "Please use the `with_session` context manager if possible or otherwise "
            "pass in a Session to the constructor."
        )
        self._session = self._initialize_session()
        return self._session

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
    @abstractmethod
    def access_token(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def refresh_token(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def load_api_key(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def refresh_access_token(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def make_request(
        self,
        ri: RequestInfo,
        allow_retry: bool = True
    ) -> ResponseInfo:
        raise NotImplementedError

    @abstractmethod
    def login(self) -> TokensInfo:
        raise NotImplementedError

    @abstractmethod
    def jwt_header(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def refresh_jwt_header(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def api_key_header(self) -> dict:
        raise NotImplementedError

    def _get_api_key_url(self) -> str:
        return self.build_url(
            namespace=DataSourcesNamespaces.AUTH,
            subdomains=["api-key"]
        )

    def _get_refresh_access_token_url(self) -> str:
        return self.build_url(
            namespace=DataSourcesNamespaces.AUTH,
            subdomains=["refresh-session"]
        )



    def build_login_request_info(self) -> RequestInfo:
        url = self.build_url(
            namespace=DataSourcesNamespaces.AUTH,
            subdomains=["login"]
        )
        auth = self.auth
        return RequestInfo(
            type_=RequestType.POST,
            url=url,
            json_={
                "email": auth.email,
                "password": auth.password
            }
        )

    def get_http_method(self, type_: RequestType) -> callable:
        return getattr(self.session, type_.value.lower())