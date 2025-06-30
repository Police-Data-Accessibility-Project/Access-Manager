# Access-Manager

This is a small package that makes it easy to access the PDAP API.

It is utilized in several other PDAP repositories


## Usage

Utilizes an `aiohttp` client session, which can either be passed into the constructor, or automatically generated when using the AccessManager as a context manager.

```python
from pdap_access_manager import AccessManager
from pdap_access_manager.models.request import RequestInfo
from pdap_access_manager.enums import DataSourcesNamespaces, RequestType

async def main():
    async with AccessManager("email", "password") as am:
        url = am.build_url(
            namespace=DataSourcesNamespaces.SEARCH,
            subdomains=['follow'],  
        )
        await am.make_request(
            RequestInfo(
                url=url,
                type_=RequestType.GET,
                headers=am.jwt_header()
            )
        )

```