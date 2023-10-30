from fastapi import HTTPException


class RepositoryNotFoundException(HTTPException):
    pass


class UnauthorizedRepositoryAccessException(HTTPException):
    pass
