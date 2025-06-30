from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from pdap_access_manager.access_manager import AccessManager
from pdap_access_manager.models.auth import AuthInfo


@pytest.fixture
def access_manager():
    mock_session = AsyncMock(
        name="mock_session",
        spec=ClientSession
    )
    access_manager = AccessManager(
        auth=AuthInfo(
            email="email",
            password="password"
        ),
        session=mock_session,
    )
    return access_manager
