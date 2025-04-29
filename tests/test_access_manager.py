from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession, ClientResponseError

from pdap_access_manager.AccessManager import AccessManager, RequestInfo, RequestType, CustomHTTPException


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

async def test_access_manager_happy_path(access_manager):

    # Mocking the method (e.g., get/post) and the response context manager
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "key": "value"
    }
    mock_response.raise_for_status.return_value = None

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_response
    access_manager.session.post.return_value = mock_cm

    ri = RequestInfo(
        type_=RequestType.POST,
        url="url",
        json_={"email": "email", "password": "password"}
    )

    result = await access_manager.make_request(ri)

    assert result.status_code == HTTPStatus.OK
    assert result.data == {
        "key": "value"
    }

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
    access_manager.session.get = mock_session_get

    ri = RequestInfo(
        type_=RequestType.GET,
        url="url"
    )

    result = await access_manager.make_request(ri)

    assert result.data == {"retried": True}
    access_manager.refresh_access_token.assert_called_once()

async def test_access_manager_refresh_access_token_failure_no_retry(access_manager):
    """
    If the request made by refresh_access_token fails,
    it should not be retried
    :return:
    """
    access_manager.jwt_header = AsyncMock(return_value={"Authorization": "Bearer token"})
    post_response = MagicMock(name="post_response")
    post_response.status = 200
    post_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=None,
        status=500,
        message="Interal Server Error"
    )

    mock_session_post = MagicMock(name="mock_session_post")
    mock_session_post.return_value.__aenter__.return_value = post_response
    access_manager.session.post = mock_session_post

    with pytest.raises(CustomHTTPException):
        await access_manager.refresh_access_token()

    post_response.raise_for_status.assert_called_once()
