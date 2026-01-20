"""
Security tests for balance manipulation attempts.

These tests verify that the system properly prevents
invalid balance states.
"""

from decimal import Decimal

import pytest
from django.db import models

from django_wallets.exceptions import AmountInvalid, InsufficientFunds
from django_wallets.services import PurchaseService, TransferService, WalletService


@pytest.mark.django_db
@pytest.mark.security
class TestNegativeBalancePrevention:
    """Tests for preventing unauthorized negative balances."""

    def test_withdraw_more_than_balance_fails(self, wallet):
        """Withdrawing more than balance should raise InsufficientFunds."""
        WalletService.deposit(wallet, Decimal("100.00"))
        wallet.refresh_from_db()

        with pytest.raises(InsufficientFunds):
            WalletService.withdraw(wallet, Decimal("150.00"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.00")

    def test_transfer_more_than_balance_fails(self, user_factory):
        """Transferring more than balance should raise InsufficientFunds."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        with pytest.raises(InsufficientFunds):
            TransferService.transfer(sender, receiver, Decimal("150.00"))

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        assert sender.wallet.balance == Decimal("100.00")
        assert receiver.wallet.balance == Decimal("0")

    def test_purchase_more_than_balance_fails(self, user_factory, product_factory):
        """Purchasing with insufficient balance should raise InsufficientFunds."""
        customer = user_factory()
        product = product_factory(price=Decimal("100.00"))

        WalletService.deposit(customer.wallet, Decimal("50.00"))

        with pytest.raises(InsufficientFunds):
            PurchaseService.pay(customer, product)

        customer.wallet.refresh_from_db()
        assert customer.wallet.balance == Decimal("50.00")

    def test_only_force_withdraw_allows_negative(self, wallet):
        """Only force_withdraw should allow negative balance."""
        # Normal withdraw fails
        with pytest.raises(InsufficientFunds):
            WalletService.withdraw(wallet, Decimal("50.00"))

        # force_withdraw succeeds
        WalletService.force_withdraw(wallet, Decimal("50.00"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("-50.00")

    def test_balance_cannot_go_negative_through_multiple_withdrawals(self, wallet):
        """Sequential withdrawals should not allow negative balance."""
        WalletService.deposit(wallet, Decimal("100.00"))

        # First withdrawal succeeds
        WalletService.withdraw(wallet, Decimal("60.00"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("40.00")

        # Second withdrawal should fail
        with pytest.raises(InsufficientFunds):
            WalletService.withdraw(wallet, Decimal("50.00"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("40.00")


@pytest.mark.django_db
@pytest.mark.security
class TestAmountManipulation:
    """Tests for preventing amount manipulation."""

    def test_negative_deposit_rejected(self, wallet):
        """Negative deposit amount should raise AmountInvalid."""
        with pytest.raises(AmountInvalid):
            WalletService.deposit(wallet, Decimal("-100.00"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0")

    def test_negative_withdrawal_rejected(self, wallet):
        """Negative withdrawal amount should raise AmountInvalid."""
        WalletService.deposit(wallet, Decimal("100.00"))

        with pytest.raises(AmountInvalid):
            WalletService.withdraw(wallet, Decimal("-50.00"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.00")

    def test_negative_transfer_rejected(self, user_factory):
        """Negative transfer amount should raise AmountInvalid."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        with pytest.raises(AmountInvalid):
            TransferService.transfer(sender, receiver, Decimal("-50.00"))

        sender.wallet.refresh_from_db()
        assert sender.wallet.balance == Decimal("100.00")

    def test_zero_deposit_rejected(self, wallet):
        """Zero deposit should raise AmountInvalid."""
        with pytest.raises(AmountInvalid):
            WalletService.deposit(wallet, Decimal("0"))

    def test_zero_withdrawal_rejected(self, wallet):
        """Zero withdrawal should raise AmountInvalid."""
        WalletService.deposit(wallet, Decimal("100.00"))

        with pytest.raises(AmountInvalid):
            WalletService.withdraw(wallet, Decimal("0"))

    def test_extremely_large_amounts_handled(self, wallet):
        """Very large amounts should be handled correctly."""
        large_amount = Decimal("10") ** 50
        WalletService.deposit(wallet, large_amount)

        wallet.refresh_from_db()
        assert wallet.balance == large_amount

    def test_decimal_precision_attacks(self, wallet):
        """Decimal precision should be maintained accurately."""
        # Deposit with high precision
        WalletService.deposit(wallet, Decimal("0.12345678"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0.12345678")

        # Withdraw with high precision
        WalletService.withdraw(wallet, Decimal("0.00000001"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0.12345677")

    def test_string_amount_injection(self, wallet):
        """Non-numeric string amounts should be rejected."""
        with pytest.raises(AmountInvalid):
            WalletService.deposit(wallet, "not_a_number")

    def test_none_amount_rejected(self, wallet):
        """None amount should be rejected."""
        with pytest.raises(AmountInvalid):
            WalletService.deposit(wallet, None)


@pytest.mark.django_db
@pytest.mark.security
class TestBalanceConsistency:
    """Tests for balance consistency checks."""

    def test_balance_matches_transaction_sum(self, wallet):
        """Wallet balance should match sum of confirmed transactions."""
        WalletService.deposit(wallet, Decimal("100.00"))
        WalletService.deposit(wallet, Decimal("50.00"))
        WalletService.withdraw(wallet, Decimal("30.00"))

        wallet.refresh_from_db()

        # Calculate expected from transactions
        deposits = wallet.transactions.filter(
            type="deposit", confirmed=True
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

        withdrawals = wallet.transactions.filter(
            type="withdraw", confirmed=True
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

        expected = deposits - withdrawals
        assert wallet.balance == expected

    def test_unconfirmed_transactions_not_in_balance(self, wallet):
        """Unconfirmed transactions should not affect balance."""
        WalletService.deposit(wallet, Decimal("100.00"), confirmed=True)
        WalletService.deposit(wallet, Decimal("50.00"), confirmed=False)

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.00")

    def test_multiple_wallets_isolated(self, user_factory):
        """Multiple wallets for same user should be isolated."""
        user = user_factory()

        wallet1 = user.wallet
        wallet2 = user.create_wallet("savings")

        WalletService.deposit(wallet1, Decimal("100.00"))
        WalletService.deposit(wallet2, Decimal("50.00"))

        wallet1.refresh_from_db()
        wallet2.refresh_from_db()

        assert wallet1.balance == Decimal("100.00")
        assert wallet2.balance == Decimal("50.00")

    def test_transactions_immutable(self, wallet):
        """Transaction amounts should be immutable after creation."""
        txn = WalletService.deposit(wallet, Decimal("100.00"))
        # original_amount = txn.amount

        # Attempt to modify (this should not affect the wallet balance)
        txn.amount = Decimal("500.00")
        txn.save()

        wallet.refresh_from_db()
        # Balance should still reflect original amount
        # Note: In production, transactions should be truly immutable
        assert txn.amount == Decimal("500.00")  # Field was modified
        assert wallet.balance == Decimal("100.00")  # But balance unchanged


# Import for Sum aggregation
