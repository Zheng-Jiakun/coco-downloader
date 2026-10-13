# coding: utf-8

NETWORK_ERROR_CONNECTION = "connection"
NETWORK_ERROR_HTTP_STATUS = "http_status"
NETWORK_ERROR_PROXY = "proxy"
NETWORK_ERROR_REDIRECT = "redirect"
NETWORK_ERROR_SSL = "ssl"
NETWORK_ERROR_TIMEOUT = "timeout"
NETWORK_ERROR_UNKNOWN = "unknown"


class ProviderNetworkError(Exception):
    """Network error that should be surfaced to the UI."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
