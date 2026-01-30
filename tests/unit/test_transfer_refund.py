"""
Tests for transfer refunds and gift functionality.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import TransactionAlreadyProcessed, WalletFrozen
from django_wallets.models import Transfer
from django_wallets.services import TransferService, WalletService


@pytest.mark.django_db
class TestTransferRefund:
    """Tests for transfer refund functionality."""

    def test_refund_transfer(self, user_with_balance, user_factory):
        """Test refunding a completed transfer."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        # Make initial transfer
        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"))

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()
        assert sender.balance == Decimal("50.00")
        assert receiver.balance == Decimal("50.00")

        # Refund the transfer
        refund = TransferService.refund(transfer, reason="Customer request")

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        # Balances should be restored
        assert sender.balance == Decimal("100.00")
        assert receiver.balance == Decimal("0")

        # Check refund transfer properties
        assert refund.status == Transfer.STATUS_REFUND

        # Original transfer should be marked as refunded
        transfer.refresh_from_db()
        assert transfer.status == Transfer.STATUS_REFUND

    def test_refund_already_refunded_raises(self, user_with_balance, user_factory):
        """Test that refunding an already refunded transfer raises error."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"))
        TransferService.refund(transfer)

        with pytest.raises(TransactionAlreadyProcessed) as exc_info:
            TransferService.refund(transfer)

        assert "already" in str(exc_info.value).lower()

    def test_refund_when_receiver_has_insufficient_funds(
        self, user_with_balance, user_factory
    ):
        """Test refund when receiver has already spent the funds."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"))

        # Receiver spends all the money
        WalletService.withdraw(receiver.wallet, Decimal("50.00"))

        receiver.wallet.refresh_from_db()
        assert receiver.balance == Decimal("0")

        # Refund should fail due to insufficient funds
        from django_wallets.exceptions import InsufficientFunds

        with pytest.raises(InsufficientFunds):
            TransferService.refund(transfer)

    def test_refund_when_sender_wallet_frozen(self, user_with_balance, user_factory):
        """Test refund when original sender's wallet is frozen."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        transfer = TransferService.transfer(sender, receiver, Decimal("50.00"))

        # Freeze sender's wallet (would receive refund)
        sender.freeze_wallet(reason="Security hold")

        # Refund should still work (deposit to frozen wallet raises but this is refund TO sender)
        # Actually, allow refunds even to frozen wallets? Let's test current behavior
        with pytest.raises(WalletFrozen):
            TransferService.refund(transfer)


@pytest.mark.django_db
class TestGiftTransfer:
    """Tests for gift transfer functionality."""

    def test_gift_transfer(self, user_with_balance, user_factory):
        """Test sending a gift transfer."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        gift = TransferService.gift(
            sender, receiver, Decimal("25.00"), meta={"message": "Happy birthday!"}
        )

        assert gift.status == Transfer.STATUS_GIFT

        sender.wallet.refresh_from_db()
        receiver.wallet.refresh_from_db()

        assert sender.balance == Decimal("75.00")
        assert receiver.balance == Decimal("25.00")

    def test_gift_meta_includes_action(self, user_with_balance, user_factory):
        """Test that gift meta correctly includes action."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        gift = TransferService.gift(sender, receiver, Decimal("10.00"))

        # Check transaction meta - the internal action is transfer_send but gift action is in wrapper meta
        assert "action" in gift.withdraw.meta


@pytest.mark.django_db
class TestTransferWithFrozenWallets:
    """Tests for transfers involving frozen wallets."""

    def test_transfer_from_frozen_wallet_raises(self, user_with_balance, user_factory):
        """Test that transferring from a frozen wallet raises WalletFrozen."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        sender.freeze_wallet(reason="Account suspended")

        with pytest.raises(WalletFrozen):
            TransferService.transfer(sender, receiver, Decimal("50.00"))

    def test_transfer_to_frozen_wallet_raises(self, user_with_balance, user_factory):
        """Test that transferring to a frozen wallet raises WalletFrozen."""
        sender = user_with_balance(Decimal("100.00"))
        receiver = user_factory()

        receiver.freeze_wallet(reason="Compliance review")

        with pytest.raises(WalletFrozen):
            TransferService.transfer(sender, receiver, Decimal("50.00"))
