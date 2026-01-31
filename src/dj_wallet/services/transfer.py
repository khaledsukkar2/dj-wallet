"""
Transfer service for handling wallet-to-wallet transfers and refunds.
"""

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from ..exceptions import TransactionAlreadyProcessed
from ..models import Transfer
from ..signals import transfer_completed
from .common import WalletService


class TransferService:
    """
    Service class for transfers between wallet holders.
    """

    @classmethod
    def transfer(cls, from_holder, to_holder, amount, meta=None, status=None):
        """
        Executes a transfer between two holders.

        Args:
            from_holder: The holder sending funds.
            to_holder: The holder receiving funds.
            amount: The amount to transfer.
            meta: Optional metadata dictionary.
            status: Optional transfer status (defaults to STATUS_TRANSFER).

        Returns:
            Transfer: The created transfer record.

        Raises:
            WalletFrozen: If either wallet is frozen.
            InsufficientFunds: If sender has insufficient balance.
        """
        # Ensure wallets exist
        sender_wallet = from_holder.wallet
        receiver_wallet = to_holder.wallet

        meta = meta or {}
        status = status or Transfer.STATUS_TRANSFER

        with transaction.atomic():
            # DEADLOCK PREVENTION:
            # To prevent deadlocks when two users transfer to each other simultaneously,
            # we lock wallets in a consistent order (by ID).
            wallets_to_lock = sorted([sender_wallet.pk, receiver_wallet.pk])

            # Lock in consistent order
            from ..models import Wallet

            for pk in wallets_to_lock:
                Wallet.objects.select_for_update().get(pk=pk)

            # 1. Withdraw from sender (this acquires the lock on sender_wallet)
            withdraw_txn = WalletService.withdraw(
                sender_wallet,
                amount,
                meta={**meta, "action": "transfer_send"},
                confirmed=True,
            )

            # 2. Deposit to receiver (this acquires the lock on receiver_wallet)
            deposit_txn = WalletService.deposit(
                receiver_wallet,
                amount,
                meta={**meta, "action": "transfer_receive"},
                confirmed=True,
            )

            # 3. Create Transfer record linking the two
            transfer_record = Transfer.objects.create(
                from_object=sender_wallet,
                to_object=receiver_wallet,
                withdraw=withdraw_txn,
                deposit=deposit_txn,
                status=status,
                fee=0,
                discount=0,
            )

            # Send signal
            transfer_completed.send(
                sender=cls,
                transfer=transfer_record,
                from_wallet=sender_wallet,
                to_wallet=receiver_wallet,
            )

            return transfer_record

    @classmethod
    def refund(cls, transfer, reason=""):
        """
        Refund a completed transfer, reversing both transactions.

        Args:
            transfer: The transfer to refund.
            reason: Optional reason for the refund.

        Returns:
            Transfer: The new refund transfer record.

        Raises:
            TransactionAlreadyProcessed: If transfer is already refunded.
            WalletFrozen: If either wallet is frozen.
        """
        with transaction.atomic():
            # Lock the transfer record
            locked_transfer = Transfer.objects.select_for_update().get(pk=transfer.pk)

            if locked_transfer.status == Transfer.STATUS_REFUND:
                raise TransactionAlreadyProcessed(
                    _("Transfer has already been refunded.")
                )

            # Get the original sender and receiver wallets
            original_sender_wallet = locked_transfer.withdraw.wallet
            original_receiver_wallet = locked_transfer.deposit.wallet

            # Calculate refund amount (original amount minus any fees)
            refund_amount = locked_transfer.deposit.amount

            meta = {
                "action": "refund",
                "original_transfer": str(locked_transfer.uuid),
                "reason": reason or "Transfer refund",
            }

            # Reverse: withdraw from original receiver, deposit to original sender
            withdraw_txn = WalletService.withdraw(
                original_receiver_wallet,
                refund_amount,
                meta={**meta, "action": "refund_withdraw"},
                confirmed=True,
            )

            deposit_txn = WalletService.deposit(
                original_sender_wallet,
                refund_amount,
                meta={**meta, "action": "refund_deposit"},
                confirmed=True,
            )

            # Mark original transfer as refunded
            locked_transfer.status = Transfer.STATUS_REFUND
            locked_transfer.save(update_fields=["status", "updated_at"])

            # Create refund transfer record
            refund_transfer = Transfer.objects.create(
                from_object=original_receiver_wallet,
                to_object=original_sender_wallet,
                withdraw=withdraw_txn,
                deposit=deposit_txn,
                status=Transfer.STATUS_REFUND,
                fee=0,
                discount=0,
            )

            # Send signal
            transfer_completed.send(
                sender=cls,
                transfer=refund_transfer,
                from_wallet=original_receiver_wallet,
                to_wallet=original_sender_wallet,
            )

            return refund_transfer

    @classmethod
    def gift(cls, from_holder, to_holder, amount, meta=None):
        """
        Send a gift transfer (convenience method with GIFT status).

        Args:
            from_holder: The holder sending the gift.
            to_holder: The holder receiving the gift.
            amount: The amount to gift.
            meta: Optional metadata dictionary.

        Returns:
            Transfer: The created transfer record.
        """
        meta = meta or {}
        meta["action"] = "gift"
        return cls.transfer(from_holder, to_holder, amount, meta, Transfer.STATUS_GIFT)
