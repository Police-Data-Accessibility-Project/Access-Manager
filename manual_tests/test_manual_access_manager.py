from aiohttp import ClientSession
from environs import Env

from pdap_access_manager.AccessManager import AccessManager, RequestInfo, RequestType, Namespaces


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
            namespace=Namespaces.PERMISSIONS,
        )
        jwt_header_pre_refresh = await access_manager.jwt_header()
        await access_manager.refresh_access_token()
        jwt_header_post_refresh = await access_manager.jwt_header()
        assert jwt_header_pre_refresh != jwt_header_post_refresh
