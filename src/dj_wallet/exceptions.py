# dj_wallet/exceptions.py


class WalletException(Exception):
    """Base exception for wallet errors."""

    pass


class AmountInvalid(WalletException):
    """Raised when amount is negative or invalid type."""

    pass


class BalanceIsEmpty(WalletException):
    """Raised when balance is insufficient."""

    pass


class InsufficientFunds(WalletException):
    """Raised when withdrawal exceeds balance."""

    pass


class ConfirmedInvalid(WalletException):
    """Raised when trying to confirm an already confirmed transaction."""

    pass


class WalletOwnerInvalid(WalletException):
    """Raised when models don't match."""

    pass


class ProductNotAvailable(WalletException):
    """Raised when a product is not available."""

    pass


class WalletFrozen(WalletException):
    """Raised when attempting operations on a frozen wallet."""

    pass


class TransactionAlreadyProcessed(WalletException):
    """Raised when trying to confirm/reject a non-pending transaction."""

    pass


class TransactionExpired(WalletException):
    """Raised when trying to confirm an expired transaction."""

    pass
