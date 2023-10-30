from fastapi import HTTPException

class InvalidFileSizeException(HTTPException):
    pass

class InvalidFileTypeException(HTTPException):
    pass

class UserNotFoundException(HTTPException):
    pass

class UserAlreadyExistsException(HTTPException):
    pass


class IncorrectFieldsException(HTTPException):
    pass


class MissingUserFieldsException(HTTPException):
    pass


class InvalidRefreshTokenException(HTTPException):
    pass


class InvalidCredentialsException(HTTPException):
    pass


class InvalidGrantTypeException(HTTPException):
    pass
