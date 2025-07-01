from enum import Enum


class RequestType(str, Enum):
    POST = "POST"
    PUT = "PUT"
    GET = "GET"
    DELETE = "DELETE"


class DataSourcesNamespaces(Enum):
    AUTH = "auth"
    LOCATIONS = "locations"
    PERMISSIONS = "permissions"
    SEARCH = "search"
    AGENCIES = "agencies"
    DATA_SOURCES = "data-sources"
    TYPEAHEAD = "typeahead"
    DATA_REQUESTS = "data-requests"
    USER = "user"
    METRICS = "metrics"
    SOURCE_COLLECTOR = 'source-collector'
    MATCH = "match"
    CHECK = "check"
    NOTIFICATIONS = "notifications"


class SourceCollectorNamespaces(Enum):
    COLLECTORS = "collector"
    SEARCH = "search"
    ANNOTATE = "annotate"
