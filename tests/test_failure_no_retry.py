from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientResponseError

from pdap_access_manager.models.tokens import TokensInfo


async def test_access_manager_refresh_access_token_failure_no_retry(
    access_manager
):
    """
    If the request made by refresh_access_token fails,
    it should not be retried,
    and a new login should be performed
    :return:
    """

    access_manager.jwt_header = AsyncMock(return_value={"Authorization": "Bearer token"})

    access_manager.login = AsyncMock(
        name="mock_login",
        return_value=TokensInfo(
            access_token="access_token",
            refresh_token="refresh_token"
        )
    )
    post_response = MagicMock(name="post_response")
    post_response.status = 200
    post_response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=None,
        status=HTTPStatus.UNAUTHORIZED.value,
        message="Internal Server Error"
    )

    mock_session_post = MagicMock(name="mock_session_post")
    mock_session_post.return_value.__aenter__.return_value = post_response
    access_manager.session.post = mock_session_post

    await access_manager.refresh_access_token()

    post_response.raise_for_status.assert_called_once()

    # Check that login called Twice
    assert access_manager.login.call_count == 2
