"""
Unit tests for TransferService.

Tests for transferring funds between wallet holders.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import InsufficientFunds
from django_wallets.models import Transfer
from django_wallets.services import TransferService, WalletService


@pytest.mark.django_db
class TestTransferService:
    """Tests for TransferService.transfer()."""

    def test_transfer_basic(self, user_factory):
        """Basic transfer should move funds between users."""
        sender = user_factory()
        receiver = user_factory()

        # Fund sender's wallet
        WalletService.deposit(sender.wallet, Decimal("100.00"))

        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"))

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        assert sender.wallet.balance == Decimal("50.00")
        assert receiver.wallet.balance == Decimal("50.00")
        assert transfer is not None

    def test_transfer_creates_transfer_record(self, user_factory):
        """Transfer should create a Transfer record."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"))

        assert transfer.pk is not None
        assert transfer.status == Transfer.STATUS_PAID

    def test_transfer_links_transactions(self, user_factory):
        """Transfer should link withdraw and deposit transactions."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"))

        assert transfer.withdraw is not None
        assert transfer.deposit is not None
        assert transfer.withdraw.amount == Decimal("50.00")
        assert transfer.deposit.amount == Decimal("50.00")

    def test_transfer_with_metadata(self, user_factory):
        """Transfer should pass metadata to transactions."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        meta = {"reason": "payment", "order_id": 123}
        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"), meta=meta)

        assert "action" in transfer.withdraw.meta
        assert "order_id" in transfer.withdraw.meta

    def test_transfer_insufficient_funds(self, user_factory):
        """Transfer with insufficient funds should raise InsufficientFunds."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("50.00"))

        with pytest.raises(InsufficientFunds):
            TransferService.transfer(sender, receiver, Decimal("100.00"))

    def test_transfer_exact_balance(self, user_factory):
        """Transfer of exact balance should leave sender with zero."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        TransferService.transfer(sender, receiver, Decimal("100.00"))

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        assert sender.wallet.balance == Decimal("0")
        assert receiver.wallet.balance == Decimal("100.00")

    def test_transfer_small_amount(self, user_factory):
        """Transfer should handle small amounts correctly."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        TransferService.transfer(sender, receiver, Decimal("0.01"))

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        assert sender.wallet.balance == Decimal("99.99")
        assert receiver.wallet.balance == Decimal("0.01")

    def test_transfer_preserves_total(self, user_factory):
        """Total funds should be preserved after transfer."""
        sender = user_factory()
        receiver = user_factory()

        initial_amount = Decimal("100.00")
        transfer_amount = Decimal("35.50")

        WalletService.deposit(sender.wallet, initial_amount)

        TransferService.transfer(sender, receiver, transfer_amount)

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        total = sender.wallet.balance + receiver.wallet.balance
        assert total == initial_amount

    def test_multiple_transfers(self, user_factory):
        """Multiple transfers should work correctly."""
        sender = user_factory()
        receiver = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))

        TransferService.transfer(sender, receiver, Decimal("20.00"))
        TransferService.transfer(sender, receiver, Decimal("30.00"))

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        assert sender.wallet.balance == Decimal("50.00")
        assert receiver.wallet.balance == Decimal("50.00")
