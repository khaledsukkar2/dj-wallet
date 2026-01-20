"""
Security tests for race conditions.

Tests to verify that concurrent operations are handled correctly.
Note: These tests require a database that supports concurrent writes (PostgreSQL, MySQL).
SQLite will be skipped as it doesn't support true concurrent transactions.
"""

import threading
from decimal import Decimal

import pytest
from django.conf import settings
from django.db import connection

from django_wallets.exceptions import InsufficientFunds
from django_wallets.services import TransferService, WalletService

# Skip concurrent tests on SQLite
sqlite_skip = pytest.mark.skipif(
    "sqlite" in settings.DATABASES["default"]["ENGINE"],
    reason="SQLite doesn't support concurrent writes"
)


@sqlite_skip
@pytest.mark.django_db(transaction=True)
@pytest.mark.security
class TestConcurrentDeposits:
    """Tests for concurrent deposit operations."""

    def test_concurrent_deposits_correct_sum(self, wallet):
        """Multiple concurrent deposits should sum correctly."""
        num_threads = 10
        deposit_amount = Decimal("100.00")
        errors = []

        def deposit():
            try:
                WalletService.deposit(wallet, deposit_amount)
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        threads = [threading.Thread(target=deposit) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        wallet.refresh_from_db()

        assert len(errors) == 0
        assert wallet.balance == deposit_amount * num_threads

    def test_rapid_successive_deposits(self, wallet):
        """Rapid deposits should all be recorded."""
        num_deposits = 50

        for _ in range(num_deposits):
            WalletService.deposit(wallet, Decimal("1.00"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("50.00")

        # Verify all transactions recorded
        assert wallet.transactions.filter(type="deposit").count() == num_deposits


@sqlite_skip
@pytest.mark.django_db(transaction=True)
@pytest.mark.security
class TestConcurrentWithdrawals:
    """Tests for concurrent withdrawal operations."""

    def test_concurrent_withdrawals_respect_balance(self, wallet):
        """Concurrent withdrawals should not exceed balance."""
        # Fund wallet with 500
        WalletService.deposit(wallet, Decimal("500.00"))
        wallet.refresh_from_db()

        num_threads = 10
        withdraw_amount = Decimal("100.00")
        success_count = [0]
        failure_count = [0]
        lock = threading.Lock()

        def withdraw():
            try:
                WalletService.withdraw(wallet, withdraw_amount)
                with lock:
                    success_count[0] += 1
            except InsufficientFunds:
                with lock:
                    failure_count[0] += 1
            finally:
                connection.close()

        threads = [threading.Thread(target=withdraw) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        wallet.refresh_from_db()

        # At most 5 should succeed (500 / 100)
        assert success_count[0] <= 5
        assert wallet.balance >= Decimal("0")

    def test_double_spend_prevention(self, wallet):
        """Simultaneous attempts to spend same funds should not both succeed."""
        WalletService.deposit(wallet, Decimal("100.00"))
        wallet.refresh_from_db()

        results = {"success": 0, "failure": 0}
        lock = threading.Lock()

        def try_withdraw():
            try:
                WalletService.withdraw(wallet, Decimal("100.00"))
                with lock:
                    results["success"] += 1
            except InsufficientFunds:
                with lock:
                    results["failure"] += 1
            finally:
                connection.close()

        t1 = threading.Thread(target=try_withdraw)
        t2 = threading.Thread(target=try_withdraw)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        wallet.refresh_from_db()

        # Only one should succeed
        assert results["success"] == 1
        assert results["failure"] == 1
        assert wallet.balance == Decimal("0")


@sqlite_skip
@pytest.mark.django_db(transaction=True)
@pytest.mark.security
class TestConcurrentTransfers:
    """Tests for concurrent transfer operations."""

    def test_concurrent_transfers_preserve_total(self, user_factory):
        """Concurrent transfers should preserve total funds."""
        user_a = user_factory()
        user_b = user_factory()

        WalletService.deposit(user_a.wallet, Decimal("1000.00"))

        num_threads = 10
        transfer_amount = Decimal("50.00")

        def transfer():
            try:
                TransferService.transfer(user_a, user_b, transfer_amount)
            except InsufficientFunds:
                pass  # Expected for some threads
            finally:
                connection.close()

        threads = [threading.Thread(target=transfer) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        user_a.wallet.refresh_from_db()
        user_b.wallet.refresh_from_db()

        total = user_a.wallet.balance + user_b.wallet.balance
        assert total == Decimal("1000.00")
