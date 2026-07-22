class ApiProviderException(Exception):
    """Base exception for ApiProvider errors."""
    def __init__(self, message, extra=None):
        super().__init__(message)
        self.message = message
        self.extra = extra

class ApiProviderConfigurationError(ApiProviderException):
    """Raised when an ApiProvider is missing or misconfigured."""
    pass

class ApiProviderRequestError(ApiProviderException):
    """Raised when an API request fails (e.g. timeouts, 500s)."""
    pass
