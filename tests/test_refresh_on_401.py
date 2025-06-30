from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientResponseError

from pdap_access_manager.enums import RequestType
from pdap_access_manager.models.request import RequestInfo


async def test_access_manager_refresh_on_401(access_manager):
    access_manager.refresh_access_token = AsyncMock()
    access_manager.jwt_header = AsyncMock(return_value={"Authorization": "Bearer token"})

    # First response raises 401
    first_get_response = MagicMock(name="first_get_response")
    first_get_response.raise_for_status.side_effect = ClientResponseError(
        request_info=None,
        history=None,
        status=401,
        message="Unauthorized"
    )

    # Second response succeeds
    second_get_response = AsyncMock(name="second_get_response")
    second_get_response.status = 200
    second_get_response.raise_for_status.return_value = None
    second_get_response.json.return_value = {"retried": True}

    mock_session_get = MagicMock(name="mock_session_get")
    mock_session_get.return_value.__aenter__.side_effect = [
        first_get_response,
        second_get_response
    ]
    access_manager._session.get = mock_session_get

    ri = RequestInfo(
        type_=RequestType.GET,
        url="url"
    )

    result = await access_manager.make_request(ri)

    assert result.data == {"retried": True}
    access_manager.refresh_access_token.assert_called_once()
