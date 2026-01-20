"""
Performance tests for concurrent operations.

Note: These tests require a database that supports concurrent writes.
SQLite will be skipped as it doesn't support true concurrent transactions.
"""

import threading
import time
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
@pytest.mark.performance
@pytest.mark.slow
class TestConcurrentTransferPerformance:
    """Tests for concurrent transfer performance."""

    def test_100_concurrent_deposits(self, wallet):
        """100 concurrent deposits should all complete."""
        num_threads = 100
        errors = []

        def deposit():
            try:
                WalletService.deposit(wallet, Decimal("10.00"))
            except Exception as e:
                errors.append(e)
            finally:
                connection.close()

        start = time.time()
        threads = [threading.Thread(target=deposit) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        elapsed = time.time() - start

        wallet.refresh_from_db()

        assert len(errors) == 0, f"Errors: {errors}"
        assert wallet.balance == Decimal("1000.00")

        # Should complete in reasonable time
        assert elapsed < 60, f"Took {elapsed:.2f}s"

    def test_50_concurrent_transfers(self, user_factory):
        """50 concurrent transfers should not deadlock."""
        sender = user_factory()
        recipient = user_factory()

        # Fund sender
        WalletService.deposit(sender.wallet, Decimal("10000.00"))

        num_threads = 50
        success_count = [0]
        lock = threading.Lock()

        def transfer():
            try:
                TransferService.transfer(sender, recipient, Decimal("100.00"))
                with lock:
                    success_count[0] += 1
            except InsufficientFunds:
                pass
            finally:
                connection.close()

        threads = [threading.Thread(target=transfer) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)  # Timeout to detect deadlocks

        # elapsed = time.time() - start

        # Check no threads are still running (would indicate deadlock)
        still_running = sum(1 for t in threads if t.is_alive())
        assert still_running == 0, f"{still_running} threads still running (deadlock?)"

        sender.wallet.refresh_from_db()
        recipient.wallet.refresh_from_db()

        # Total should be preserved
        total = sender.wallet.balance + recipient.wallet.balance
        assert total == Decimal("10000.00")



@sqlite_skip
@pytest.mark.django_db(transaction=True)
@pytest.mark.performance
@pytest.mark.slow
class TestTransferScaling:
    """Tests for transfer scaling characteristics."""

    def test_transfer_time_scales_reasonably(self, user_factory):
        """Transfer time should not grow excessively with volume."""
        sender = user_factory()
        recipient = user_factory()

        WalletService.deposit(sender.wallet, Decimal("10000.00"))

        # Measure 10 transfers
        start = time.time()
        for _ in range(10):
            TransferService.transfer(sender, recipient, Decimal("1.00"))
        time_10 = time.time() - start

        # Measure another 10 transfers
        start = time.time()
        for _ in range(10):
            TransferService.transfer(sender, recipient, Decimal("1.00"))
        time_10_more = time.time() - start

        # Second batch shouldn't be much slower than first
        # Allow 50% variance
        assert time_10_more < time_10 * 1.5, "Performance degradation detected"

    def test_many_to_one_transfers(self, user_factory):
        """Many users transferring to one should work."""
        recipient = user_factory()
        senders = [user_factory() for _ in range(20)]

        # Fund all senders
        for sender in senders:
            WalletService.deposit(sender.wallet, Decimal("100.00"))

        # All transfer to recipient
        for sender in senders:
            TransferService.transfer(sender, recipient, Decimal("50.00"))

        recipient.wallet.refresh_from_db()
        assert recipient.wallet.balance == Decimal("1000.00")  # 20 * 50
