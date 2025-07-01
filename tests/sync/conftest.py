from unittest.mock import MagicMock

import pytest
from requests import Session

from pdap_access_manager.access_manager.sync import AccessManagerSync
from pdap_access_manager.models.auth import AuthInfo


@pytest.fixture
def access_manager() -> AccessManagerSync:
    mock_session = MagicMock(
        name="mock_session",
        spec=Session
    )
    access_manager = AccessManagerSync(
        auth=AuthInfo(
            email="email",
            password="password"
        ),
        session=mock_session,
    )
    return access_manager
