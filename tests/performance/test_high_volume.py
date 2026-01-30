"""
Performance tests for high-volume operations.
"""

import time
from decimal import Decimal

import pytest

from django_wallets.models import Transaction
from django_wallets.services import WalletService


@pytest.mark.django_db()
@pytest.mark.performance()
@pytest.mark.slow()
class TestHighVolumeDeposits:
    """Tests for high-volume deposit operations."""

    def test_1000_deposits_time(self, wallet):
        """1000 deposits should complete in reasonable time."""
        num_deposits = 1000

        start = time.time()
        for _ in range(num_deposits):
            WalletService.deposit(wallet, Decimal("1.00"))
        elapsed = time.time() - start

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("1000.00")

        # Should complete in under 30 seconds
        assert elapsed < 30, f"Took {elapsed:.2f}s, expected < 30s"

    def test_deposit_throughput(self, wallet):
        """Measure deposits per second."""
        num_deposits = 100

        start = time.time()
        for _ in range(num_deposits):
            WalletService.deposit(wallet, Decimal("1.00"))
        elapsed = time.time() - start

        throughput = num_deposits / elapsed

        # Should achieve at least 10 deposits/second
        assert throughput >= 10, f"Only {throughput:.1f}/s, expected >= 10/s"


@pytest.mark.django_db()
@pytest.mark.performance()
@pytest.mark.slow()
class TestHighVolumeWithdrawals:
    """Tests for high-volume withdrawal operations."""

    def test_1000_withdrawals_time(self, wallet):
        """1000 withdrawals should complete in reasonable time."""
        # Fund wallet first
        WalletService.deposit(wallet, Decimal("1000.00"))

        num_withdrawals = 1000

        start = time.time()
        for _ in range(num_withdrawals):
            WalletService.withdraw(wallet, Decimal("1.00"))
        elapsed = time.time() - start

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0.00")

        # Should complete in under 30 seconds
        assert elapsed < 30, f"Took {elapsed:.2f}s, expected < 30s"


@pytest.mark.django_db()
@pytest.mark.performance()
@pytest.mark.slow()
class TestQueryOptimization:
    """Tests for database query optimization."""

    def test_transaction_query_time(self, wallet):
        """Querying many transactions should be efficient."""
        # Create 500 transactions
        for _ in range(250):
            WalletService.deposit(wallet, Decimal("1.00"))
            WalletService.withdraw(wallet, Decimal("0.50"))

        start = time.time()
        count = Transaction.objects.filter(wallet=wallet).count()
        elapsed = time.time() - start

        assert count == 500
        assert elapsed < 1.0, f"Count query took {elapsed:.2f}s"

    def test_balance_lookup_time(self, user_factory):
        """Balance lookup should be fast."""
        users = [user_factory() for _ in range(100)]

        # Fund all wallets
        for user in users:
            WalletService.deposit(user.wallet, Decimal("100.00"))

        start = time.time()
        for user in users:
            user.wallet.refresh_from_db()
            _ = user.wallet.balance
        elapsed = time.time() - start

        # 100 balance lookups should take < 1 second
        assert elapsed < 1.0, f"Took {elapsed:.2f}s for 100 lookups"

    def test_wallet_access_queries(self, user):
        """Wallet access should work correctly."""
        # First access creates wallet
        wallet = user.wallet
        assert wallet is not None

        # Second access should return same wallet
        wallet2 = user.wallet
        assert wallet.pk == wallet2.pk
