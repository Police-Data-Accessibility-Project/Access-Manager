from pdap_access_manager.models.auth import AuthInfo

# Access-Manager

This is a small package that makes it easy to access the PDAP API.

It is utilized in several other PDAP repositories


## Usage

Utilizes an `aiohttp` client session, which can either be passed into the constructor, or automatically generated when using the AccessManager as a context manager.

```python
from pdap_access_manager.access_manager.async_ import AccessManagerAsync
from pdap_access_manager.models.request import RequestInfo
from pdap_access_manager.models.auth import AuthInfo
from pdap_access_manager.enums import RequestType

async def main():
    auth_info = AuthInfo(
        email="email",
        password="password"
    )
    async with AccessManagerAsync(auth_info) as am:
        url = f"{am.data_sources_url}/search/follow"
        await am.make_request(
            RequestInfo(
                url=url,
                type_=RequestType.GET,
                headers=am.jwt_header()
            )
        )

```