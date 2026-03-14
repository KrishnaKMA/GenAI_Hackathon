"""
Custom HTTP exceptions used across all routes.
Import these instead of raising HTTPException directly.
"""

from fastapi import HTTPException, status


class ClaimNotFound(HTTPException):
    def __init__(self, claim_token: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_token}' not found",
        )


class Unauthorized(HTTPException):
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class Forbidden(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class InvalidCredentials(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTOTP(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired TOTP code",
        )


class AnalysisError(HTTPException):
    def __init__(self, detail: str = "ML analysis failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class IBMServiceError(HTTPException):
    def __init__(self, detail: str = "IBM service unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
