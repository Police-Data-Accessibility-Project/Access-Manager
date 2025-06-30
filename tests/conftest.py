from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from pdap_access_manager.access_manager import AccessManager


@pytest.fixture
def access_manager():
    mock_session = AsyncMock(
        name="mock_session",
        spec=ClientSession
    )
    access_manager = AccessManager(
        email="email",
        password="password",
        session=mock_session,
    )
    return access_manager
