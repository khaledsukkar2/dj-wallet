"""
Security tests for balance manipulation prevention.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import AmountInvalid, InsufficientFunds
from django_wallets.services import WalletService


@pytest.mark.django_db
@pytest.mark.security
class TestNegativeBalancePrevention:
    """Tests for preventing unauthorized negative balances."""

    def test_withdraw_more_than_balance_fails(self, funded_wallet):
        """Normal withdraw should not allow negative balance."""
        with pytest.raises(InsufficientFunds):
            WalletService.withdraw(funded_wallet, Decimal("150.00"))

        funded_wallet.refresh_from_db()
        assert funded_wallet.balance == Decimal("100.00")

    def test_only_force_withdraw_allows_negative(self, wallet):
        """Only force_withdraw should allow negative balance."""
        # Normal withdraw fails
        with pytest.raises(InsufficientFunds):
            WalletService.withdraw(wallet, Decimal("50.00"))

        # Force withdraw succeeds
        WalletService.force_withdraw(wallet, Decimal("50.00"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("-50.00")


@pytest.mark.django_db
@pytest.mark.security
class TestAmountManipulation:
    """Tests for preventing amount manipulation."""

    def test_negative_deposit_rejected(self, wallet):
        """Negative deposit should be rejected."""
        with pytest.raises(AmountInvalid):
            WalletService.deposit(wallet, Decimal("-100.00"))

    def test_negative_withdrawal_rejected(self, funded_wallet):
        """Negative withdrawal should be rejected."""
        with pytest.raises(AmountInvalid):
            WalletService.withdraw(funded_wallet, Decimal("-50.00"))

    def test_zero_amount_rejected(self, wallet):
        """Zero amount should be rejected."""
        with pytest.raises(AmountInvalid):
            WalletService.deposit(wallet, Decimal("0"))

        with pytest.raises(AmountInvalid):
            WalletService.withdraw(wallet, Decimal("0"))

    def test_extremely_large_amount(self, wallet):
        """Very large amounts should be handled."""
        large_amount = Decimal("10") ** 50
        WalletService.deposit(wallet, large_amount)

        wallet.refresh_from_db()
        assert wallet.balance == large_amount

    def test_decimal_precision_maintained(self, wallet):
        """Decimal precision should be maintained."""
        WalletService.deposit(wallet, Decimal("0.00000001"))
        WalletService.deposit(wallet, Decimal("0.00000001"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0.00000002")


@pytest.mark.django_db
@pytest.mark.security
class TestBalanceConsistency:
    """Tests for balance consistency checks."""

    def test_balance_matches_transaction_sum(self, wallet):
        """Balance should equal sum of confirmed transactions."""
        from django_wallets.models import Transaction

        WalletService.deposit(wallet, Decimal("100.00"))
        WalletService.deposit(wallet, Decimal("50.00"))
        WalletService.deposit(wallet, Decimal("25.00"), confirmed=False)  # Unconfirmed
        WalletService.withdraw(wallet, Decimal("30.00"))

        wallet.refresh_from_db()

        # Calculate from transactions
        deposits = sum(
            t.amount for t in wallet.transactions.filter(
                type=Transaction.TYPE_DEPOSIT, confirmed=True
            )
        )
        withdrawals = sum(
            t.amount for t in wallet.transactions.filter(
                type=Transaction.TYPE_WITHDRAW, confirmed=True
            )
        )

        calculated_balance = deposits - withdrawals
        assert wallet.balance == calculated_balance

    def test_unconfirmed_not_in_balance(self, wallet):
        """Unconfirmed transactions should not affect balance."""
        WalletService.deposit(wallet, Decimal("100.00"), confirmed=True)
        WalletService.deposit(wallet, Decimal("50.00"), confirmed=False)

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.00")
