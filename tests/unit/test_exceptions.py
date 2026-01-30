"""
Unit tests for custom exceptions.
"""

import pytest

from django_wallets.exceptions import (
    AmountInvalid,
    BalanceIsEmpty,
    ConfirmedInvalid,
    InsufficientFunds,
    ProductNotAvailable,
    WalletException,
    WalletOwnerInvalid,
)


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_wallet_exception_is_base(self):
        """WalletException should be the base class."""
        assert issubclass(AmountInvalid, WalletException)
        assert issubclass(BalanceIsEmpty, WalletException)
        assert issubclass(InsufficientFunds, WalletException)
        assert issubclass(ConfirmedInvalid, WalletException)
        assert issubclass(WalletOwnerInvalid, WalletException)
        assert issubclass(ProductNotAvailable, WalletException)

    def test_all_inherit_from_exception(self):
        """All exceptions should inherit from base Exception."""
        assert issubclass(WalletException, Exception)

    def test_exceptions_are_catchable_as_wallet_exception(self):
        """All specific exceptions should be catchable as WalletException."""
        try:
            raise AmountInvalid("test")
        except WalletException:
            pass  # Should be caught

        try:
            raise InsufficientFunds("test")
        except WalletException:
            pass  # Should be caught


class TestExceptionMessages:
    """Tests for exception messages."""

    def test_amount_invalid_message(self):
        """AmountInvalid should preserve message."""
        exc = AmountInvalid("Invalid amount: -100")
        assert "Invalid amount" in str(exc)

    def test_insufficient_funds_message(self):
        """InsufficientFunds should preserve message."""
        exc = InsufficientFunds("Balance: 50, Required: 100")
        assert "Balance" in str(exc)
        assert "Required" in str(exc)

    def test_product_ended_message(self):
        """ProductNotAvailable should preserve message."""
        exc = ProductNotAvailable("Product out of stock")
        assert "out of stock" in str(exc)


class TestExceptionUsage:
    """Tests for proper exception raising."""

    def test_amount_invalid_raised_correctly(self):
        """AmountInvalid should be raisable."""
        with pytest.raises(AmountInvalid):
            raise AmountInvalid("test")

    def test_insufficient_funds_raised_correctly(self):
        """InsufficientFunds should be raisable."""
        with pytest.raises(InsufficientFunds):
            raise InsufficientFunds("test")

    def test_balance_is_empty_raised_correctly(self):
        """BalanceIsEmpty should be raisable."""
        with pytest.raises(BalanceIsEmpty):
            raise BalanceIsEmpty("test")

    def test_confirmed_invalid_raised_correctly(self):
        """ConfirmedInvalid should be raisable."""
        with pytest.raises(ConfirmedInvalid):
            raise ConfirmedInvalid("test")

    def test_wallet_owner_invalid_raised_correctly(self):
        """WalletOwnerInvalid should be raisable."""
        with pytest.raises(WalletOwnerInvalid):
            raise WalletOwnerInvalid("test")

    def test_product_ended_raised_correctly(self):
        """ProductNotAvailable should be raisable."""
        with pytest.raises(ProductNotAvailable):
            raise ProductNotAvailable("test")
