from aiohttp import ClientSession

from pdap_access_manager.enums import RequestType

request_methods = {
    RequestType.POST: ClientSession.post,
    RequestType.PUT: ClientSession.put,
    RequestType.GET: ClientSession.get,
    RequestType.DELETE: ClientSession.delete,
}
