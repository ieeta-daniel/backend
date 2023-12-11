from fastapi import HTTPException


class ModelNotFoundException(HTTPException):
    pass


class UnauthorizedModelAccessException(HTTPException):
    pass
