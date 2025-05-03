from aiohttp import ClientSession
from environs import Env

from pdap_access_manager.access_manager import AccessManager, RequestInfo, RequestType, DataSourcesNamespaces


async def test_access_manager_refresh_access_token():
    env = Env()
    env.read_env()

    async with ClientSession() as session:
        access_manager = AccessManager(
            email=env.str("PDAP_EMAIL"),
            password=env.str("PDAP_PASSWORD"),
            session=session,
        )
        url = access_manager.build_url(
            namespace=DataSourcesNamespaces.SEARCH,
            subdomains=['follow']
        )
        request_info = RequestInfo(
            type_=RequestType.GET,
            url=url,
            headers={"Authorization": "Bearer FalseAuth"}
        )
        response_info = await access_manager.make_request(request_info)
        assert response_info.status_code == 200
