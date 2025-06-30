from enum import Enum


class RequestType(Enum):
    POST = "POST"
    PUT = "PUT"
    GET = "GET"
    DELETE = "DELETE"


class DataSourcesNamespaces(Enum):
    AUTH = "auth"
    LOCATIONS = "locations"
    PERMISSIONS = "permissions"
    SEARCH = "search"
    DATA_SOURCES = "data-sources"
    SOURCE_COLLECTOR = 'source-collector'
    MATCH = "match"
    CHECK = "check"


class SourceCollectorNamespaces(Enum):
    COLLECTORS = "collector"
    SEARCH = "search"
    ANNOTATE = "annotate"
