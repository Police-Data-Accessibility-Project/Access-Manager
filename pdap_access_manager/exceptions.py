from http import HTTPStatus


class TokensNotSetError(Exception):
    """
    Exception raised when access and refresh tokens are not set.
    """
    pass


class AuthNotSetError(Exception):
    """
    Exception raised when auth info is not set.
    """
    pass

class IncorrectSessionError(Exception):
    """
    Exception raised when the session type is incorrect.
    """
    pass

class RequestError(Exception):
    """
    Exception raised when a request fails.
    """
    def __init__(self, message, status_code: HTTPStatus):
        super().__init__(message)
        self.status_code = status_code