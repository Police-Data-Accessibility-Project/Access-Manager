


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