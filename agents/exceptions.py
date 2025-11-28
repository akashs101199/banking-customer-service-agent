"""
Banking System Exceptions
Custom exceptions for handling banking-specific error scenarios
"""

class BankingException(Exception):
    """Base exception for all banking errors"""
    def __init__(self, message: str, user_message: str = None, next_steps: list = None):
        super().__init__(message)
        self.user_message = user_message or message
        self.next_steps = next_steps or []

class ResourceNotFoundError(BankingException):
    """Raised when a requested resource (account, card, customer) is not found"""
    pass

class InsufficientFundsError(BankingException):
    """Raised when an account has insufficient funds for a transaction"""
    pass

class AuthenticationError(BankingException):
    """Raised when authentication or authorization fails"""
    pass

class ValidationError(BankingException):
    """Raised when input validation fails"""
    pass

class ComplianceError(BankingException):
    """Raised when a transaction violates compliance rules (e.g. AML, fraud)"""
    pass
