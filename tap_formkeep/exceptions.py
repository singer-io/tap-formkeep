class formkeepError(Exception):
    """class representing Generic Http error."""

    def __init__(self, message=None, response=None):
        super().__init__(message)
        self.message = message
        self.response = response


class formkeepBackoffError(formkeepError):
    """class representing backoff error handling."""
    pass

class formkeepBadRequestError(formkeepError):
    """class representing 400 status code."""
    pass

class formkeepUnauthorizedError(formkeepError):
    """class representing 401 status code."""
    pass


class formkeepForbiddenError(formkeepError):
    """class representing 403 status code."""
    pass

class formkeepNotFoundError(formkeepError):
    """class representing 404 status code."""
    pass

class formkeepConflictError(formkeepError):
    """class representing 409 status code."""
    pass

class formkeepUnprocessableEntityError(formkeepBackoffError):
    """class representing 422 status code."""
    pass

class formkeepRateLimitError(formkeepBackoffError):
    """class representing 429 status code."""
    pass

class formkeepInternalServerError(formkeepBackoffError):
    """class representing 500 status code."""
    pass

class formkeepNotImplementedError(formkeepBackoffError):
    """class representing 501 status code."""
    pass

class formkeepBadGatewayError(formkeepBackoffError):
    """class representing 502 status code."""
    pass

class formkeepServiceUnavailableError(formkeepBackoffError):
    """class representing 503 status code."""
    pass

ERROR_CODE_EXCEPTION_MAPPING = {
    400: {
        "raise_exception": formkeepBadRequestError,
        "message": "A validation exception has occurred."
    },
    401: {
        "raise_exception": formkeepUnauthorizedError,
        "message": "The access token provided is expired, revoked, malformed or invalid for other reasons."
    },
    403: {
        "raise_exception": formkeepForbiddenError,
        "message": "You are missing the following required scopes: read"
    },
    404: {
        "raise_exception": formkeepNotFoundError,
        "message": "The resource you have specified cannot be found."
    },
    409: {
        "raise_exception": formkeepConflictError,
        "message": "The API request cannot be completed because the requested operation would conflict with an existing item."
    },
    422: {
        "raise_exception": formkeepUnprocessableEntityError,
        "message": "The request content itself is not processable by the server."
    },
    429: {
        "raise_exception": formkeepRateLimitError,
        "message": "The API rate limit for your organisation/application pairing has been exceeded."
    },
    500: {
        "raise_exception": formkeepInternalServerError,
        "message": "The server encountered an unexpected condition which prevented" \
            " it from fulfilling the request."
    },
    501: {
        "raise_exception": formkeepNotImplementedError,
        "message": "The server does not support the functionality required to fulfill the request."
    },
    502: {
        "raise_exception": formkeepBadGatewayError,
        "message": "Server received an invalid response."
    },
    503: {
        "raise_exception": formkeepServiceUnavailableError,
        "message": "API service is currently unavailable."
    }
}

