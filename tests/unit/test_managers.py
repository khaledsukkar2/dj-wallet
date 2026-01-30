"""
Unit tests for custom model managers.
"""

import pytest

from django_wallets.models import Wallet


@pytest.mark.django_db()
class TestWalletManager:
    """Tests for WalletManager."""

    def test_get_wallet_returns_existing(self, user):
        """get_wallet should return existing wallet."""
        expected = user.wallet  # Creates default wallet
        result = Wallet.objects.get_wallet(user, slug="default")
        assert result == expected

    def test_get_wallet_returns_none_if_not_exists(self, user):
        """get_wallet should return None if wallet doesn't exist."""
        result = Wallet.objects.get_wallet(user, slug="nonexistent")
        assert result is None

    def test_get_wallet_by_slug(self, user):
        """get_wallet should return correct wallet by slug."""
        _ = user.wallet  # Create default
        savings = user.create_wallet("savings")

        result = Wallet.objects.get_wallet(user, slug="savings")
        assert result == savings

    def test_get_wallet_different_holders(self, user_factory):
        """get_wallet should isolate wallets by holder."""
        user1 = user_factory()
        user2 = user_factory()

        wallet1 = user1.wallet
        wallet2 = user2.wallet

        result = Wallet.objects.get_wallet(user1)
        assert result == wallet1
        assert result != wallet2


@pytest.mark.django_db()
class TestTransactionManager:
    """Tests for TransactionManager."""

    def test_transaction_queryset_filters(self, deposit_factory, funded_wallet):
        """TransactionManager should support standard QuerySet operations."""
        from django_wallets.models import Transaction
        from django_wallets.services import WalletService

        # Create some transactions
        deposit_factory(wallet=funded_wallet)
        WalletService.withdraw(funded_wallet, 50)

        deposits = Transaction.objects.filter(type=Transaction.TYPE_DEPOSIT)
        withdrawals = Transaction.objects.filter(type=Transaction.TYPE_WITHDRAW)

        # At least 2 deposits (funded_wallet creation + deposit_factory)
        # and 1 withdrawal
        assert deposits.count() >= 2
        assert withdrawals.count() >= 1
