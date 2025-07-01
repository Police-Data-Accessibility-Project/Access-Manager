from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

from pdap_access_manager.enums import RequestType
from pdap_access_manager.models.request import RequestInfo


def test_access_manager_happy_path(access_manager):
    # Mocking the method (e.g., get/post) and the response context manager
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "key": "value"
    }
    mock_response.raise_for_status.return_value = None

    access_manager._session.post.return_value = mock_response

    ri = RequestInfo(
        type_=RequestType.POST,
        url="url",
        json_={"email": "email", "password": "password"}
    )

    result = access_manager.make_request(ri)

    assert result.status_code == HTTPStatus.OK
    assert result.data == {
        "key": "value"
    }
