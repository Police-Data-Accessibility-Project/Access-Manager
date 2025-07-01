from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientResponseError
from requests import HTTPError, Response

from pdap_access_manager.models.tokens import TokensInfo


def test_access_manager_refresh_access_token_failure_no_retry(
    access_manager
):
    """
    If the request made by refresh_access_token fails,
    it should not be retried,
    and a new login should be performed
    :return:
    """

    access_manager.jwt_header = MagicMock(return_value={"Authorization": "Bearer token"})

    access_manager.login = MagicMock(
        name="mock_login",
        return_value=TokensInfo(
            access_token="access_token",
            refresh_token="refresh_token"
        )
    )
    post_response = MagicMock(name="post_response")
    post_response.status = 200
    response = Response()
    response.status_code = HTTPStatus.UNAUTHORIZED
    post_response.raise_for_status.side_effect = HTTPError(
        response=response,
    )

    mock_session_post = MagicMock(name="mock_session_post")
    mock_session_post.return_value = post_response
    access_manager._session.post = mock_session_post

    access_manager.refresh_access_token()

    post_response.raise_for_status.assert_called_once()

    # Check that login called Twice
    assert access_manager.login.call_count == 2
