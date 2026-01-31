"""
Core wallet service providing deposit, withdraw, and transaction confirmation operations.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from ..exceptions import (
    AmountInvalid,
    InsufficientFunds,
    TransactionAlreadyProcessed,
    WalletFrozen,
)
from ..models import Transaction, Wallet
from ..signals import balance_changed, transaction_confirmed, transaction_created


class WalletService:
    """
    Service class for wallet operations including deposit, withdraw,
    and transaction confirmation workflow.
    """

    @staticmethod
    def verify_amount(amount):
        """
        Ensures amount is valid decimal and positive.

        Args:
            amount: The amount to validate.

        Returns:
            Decimal: The validated amount.

        Raises:
            AmountInvalid: If amount is not a valid positive number.
        """
        try:
            val = Decimal(
                str(amount)
            )  # Convert to string first to avoid float precision issues
        except (ValueError, InvalidOperation):
            raise AmountInvalid(_("Amount must be a number.")) from None

        if val <= 0:
            raise AmountInvalid(_("Amount must be positive."))
        return val

    @classmethod
    def _check_frozen(cls, wallet):
        """
        Check if wallet is frozen and raise exception if so.

        Args:
            wallet: The wallet to check.

        Raises:
            WalletFrozen: If the wallet is frozen.
        """
        if getattr(wallet, "is_frozen", False):
            raise WalletFrozen(
                _("Wallet '%(slug)s' is frozen: %(reason)s")
                % {
                    "slug": wallet.slug,
                    "reason": wallet.frozen_reason or "No reason provided",
                }
            )

    @classmethod
    def deposit(cls, wallet, amount, meta=None, confirmed=True):
        """
        Performs a deposit. Wraps logic in atomic block with row locking.

        Args:
            wallet: The wallet to deposit to.
            amount: The amount to deposit.
            meta: Optional metadata dictionary.
            confirmed: Whether to immediately confirm the transaction.

        Returns:
            Transaction: The created transaction record.

        Raises:
            WalletFrozen: If the wallet is frozen.
            AmountInvalid: If the amount is invalid.
        """
        amount = cls.verify_amount(amount)
        meta = meta or {}

        with transaction.atomic():
            # Lock the wallet row to prevent concurrent modifications
            locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            # Check if wallet is frozen
            cls._check_frozen(locked_wallet)

            # Determine transaction status based on confirmed flag
            status = (
                Transaction.STATUS_COMPLETED
                if confirmed
                else Transaction.STATUS_PENDING
            )

            # Create the immutable transaction record
            txn = Transaction.objects.create(
                payable=locked_wallet,
                wallet=locked_wallet,
                type=Transaction.TYPE_DEPOSIT,
                amount=amount,
                confirmed=confirmed,
                status=status,
                meta=meta,
            )

            if confirmed:
                locked_wallet.balance += amount
                locked_wallet.save()

                # Signal dispatching
                balance_changed.send(sender=cls, wallet=locked_wallet, transaction=txn)

            transaction_created.send(sender=cls, transaction=txn)

            return txn

    @classmethod
    def withdraw(cls, wallet, amount, meta=None, confirmed=True):
        """
        Performs a withdrawal. Checks for sufficient funds inside the lock.

        Args:
            wallet: The wallet to withdraw from.
            amount: The amount to withdraw.
            meta: Optional metadata dictionary.
            confirmed: Whether to immediately confirm the transaction.

        Returns:
            Transaction: The created transaction record.

        Raises:
            WalletFrozen: If the wallet is frozen.
            AmountInvalid: If the amount is invalid.
            InsufficientFunds: If balance is insufficient.
        """
        amount = cls.verify_amount(amount)
        meta = meta or {}

        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            # Check if wallet is frozen
            cls._check_frozen(locked_wallet)

            # Check balance *after* acquiring lock
            if confirmed and locked_wallet.balance < amount:
                raise InsufficientFunds(
                    _("Insufficient funds. Balance: %(balance)s, Required: %(amount)s")
                    % {"balance": locked_wallet.balance, "amount": amount}
                )

            # Determine transaction status based on confirmed flag
            status = (
                Transaction.STATUS_COMPLETED
                if confirmed
                else Transaction.STATUS_PENDING
            )

            txn = Transaction.objects.create(
                payable=locked_wallet,
                wallet=locked_wallet,
                type=Transaction.TYPE_WITHDRAW,
                amount=amount,
                confirmed=confirmed,
                status=status,
                meta=meta,
            )

            if confirmed:
                locked_wallet.balance -= amount
                locked_wallet.save()
                balance_changed.send(sender=cls, wallet=locked_wallet, transaction=txn)

            transaction_created.send(sender=cls, transaction=txn)

            return txn

    @classmethod
    def force_withdraw(cls, wallet, amount, meta=None, confirmed=True):
        """
        Withdraws even if balance is insufficient (can go negative).

        Args:
            wallet: The wallet to withdraw from.
            amount: The amount to withdraw.
            meta: Optional metadata dictionary.
            confirmed: Whether to immediately confirm the transaction.

        Returns:
            Transaction: The created transaction record.

        Raises:
            WalletFrozen: If the wallet is frozen.
            AmountInvalid: If the amount is invalid.
        """
        amount = cls.verify_amount(amount)
        meta = meta or {}

        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            # Check if wallet is frozen
            cls._check_frozen(locked_wallet)

            # Determine transaction status based on confirmed flag
            status = (
                Transaction.STATUS_COMPLETED
                if confirmed
                else Transaction.STATUS_PENDING
            )

            txn = Transaction.objects.create(
                payable=locked_wallet,
                wallet=locked_wallet,
                type=Transaction.TYPE_WITHDRAW,
                amount=amount,
                confirmed=confirmed,
                status=status,
                meta=meta,
            )

            if confirmed:
                locked_wallet.balance -= amount
                locked_wallet.save()
                balance_changed.send(sender=cls, wallet=locked_wallet, transaction=txn)

            transaction_created.send(sender=cls, transaction=txn)

            return txn

    @classmethod
    def confirm_transaction(cls, txn):
        """
        Confirm a pending transaction, applying its effect to the wallet balance.

        Args:
            txn: The transaction to confirm.

        Returns:
            Transaction: The confirmed transaction.

        Raises:
            TransactionAlreadyProcessed: If transaction is not pending.
            WalletFrozen: If the wallet is frozen.
            InsufficientFunds: If withdrawing and balance is insufficient.
        """
        with transaction.atomic():
            # Lock the transaction and wallet
            locked_txn = Transaction.objects.select_for_update().get(pk=txn.pk)

            if locked_txn.status != Transaction.STATUS_PENDING:
                raise TransactionAlreadyProcessed(
                    _("Transaction is already %(status)s, cannot confirm.")
                    % {"status": locked_txn.status}
                )

            locked_wallet = Wallet.objects.select_for_update().get(
                pk=locked_txn.wallet_id
            )

            # Check if wallet is frozen
            cls._check_frozen(locked_wallet)

            # For withdrawals, check sufficient funds
            if locked_txn.type == Transaction.TYPE_WITHDRAW:
                if locked_wallet.balance < locked_txn.amount:
                    raise InsufficientFunds(
                        _(
                            "Insufficient funds to confirm withdrawal. Balance: %(balance)s, Required: %(amount)s"
                        )
                        % {
                            "balance": locked_wallet.balance,
                            "amount": locked_txn.amount,
                        }
                    )
                locked_wallet.balance -= locked_txn.amount
            else:  # Deposit
                locked_wallet.balance += locked_txn.amount

            # Update transaction
            locked_txn.confirmed = True
            locked_txn.status = Transaction.STATUS_COMPLETED
            locked_txn.save(update_fields=["confirmed", "status", "updated_at"])

            # Update wallet
            locked_wallet.save(update_fields=["balance", "updated_at"])

            # Send signals
            balance_changed.send(
                sender=cls, wallet=locked_wallet, transaction=locked_txn
            )
            transaction_confirmed.send(sender=cls, transaction=locked_txn)

            return locked_txn

    @classmethod
    def reject_transaction(cls, txn, reason=""):
        """
        Reject a pending transaction without affecting wallet balance.

        Args:
            txn: The transaction to reject.
            reason: Optional reason for rejection.

        Returns:
            Transaction: The rejected transaction.

        Raises:
            TransactionAlreadyProcessed: If transaction is not pending.
        """
        with transaction.atomic():
            locked_txn = Transaction.objects.select_for_update().get(pk=txn.pk)

            if locked_txn.status != Transaction.STATUS_PENDING:
                raise TransactionAlreadyProcessed(
                    _("Transaction is already %(status)s, cannot reject.")
                    % {"status": locked_txn.status}
                )

            # Update transaction status to failed
            locked_txn.status = Transaction.STATUS_FAILED
            if reason:
                locked_txn.meta = locked_txn.meta or {}
                locked_txn.meta["rejection_reason"] = reason
            locked_txn.save(update_fields=["status", "meta", "updated_at"])

            return locked_txn

    @classmethod
    def reverse_transaction(cls, txn, reason=""):
        """
        Reverse a completed transaction, creating an opposite transaction.

        Args:
            txn: The transaction to reverse.
            reason: Optional reason for reversal.

        Returns:
            Transaction: The reversal transaction.

        Raises:
            TransactionAlreadyProcessed: If transaction is not completed.
            WalletFrozen: If the wallet is frozen.
            InsufficientFunds: If reversing a deposit and balance is insufficient.
        """
        with transaction.atomic():
            locked_txn = Transaction.objects.select_for_update().get(pk=txn.pk)

            if locked_txn.status != Transaction.STATUS_COMPLETED:
                raise TransactionAlreadyProcessed(
                    _(
                        "Only completed transactions can be reversed. Current status: %(status)s"
                    )
                    % {"status": locked_txn.status}
                )

            locked_wallet = Wallet.objects.select_for_update().get(
                pk=locked_txn.wallet_id
            )

            # Check if wallet is frozen
            cls._check_frozen(locked_wallet)

            # Create opposite transaction
            if locked_txn.type == Transaction.TYPE_DEPOSIT:
                # Reversing a deposit = withdrawal
                if locked_wallet.balance < locked_txn.amount:
                    raise InsufficientFunds(
                        _(
                            "Insufficient funds to reverse deposit. Balance: %(balance)s, Required: %(amount)s"
                        )
                        % {
                            "balance": locked_wallet.balance,
                            "amount": locked_txn.amount,
                        }
                    )
                locked_wallet.balance -= locked_txn.amount
                reversal_type = Transaction.TYPE_WITHDRAW
            else:
                # Reversing a withdrawal = deposit
                locked_wallet.balance += locked_txn.amount
                reversal_type = Transaction.TYPE_DEPOSIT

            # Mark original as reversed
            locked_txn.status = Transaction.STATUS_REVERSED
            locked_txn.save(update_fields=["status", "updated_at"])

            # Create reversal transaction
            reversal_meta = {
                "reversal_of": str(locked_txn.uuid),
                "reason": reason or "Transaction reversal",
            }

            reversal_txn = Transaction.objects.create(
                payable=locked_wallet,
                wallet=locked_wallet,
                type=reversal_type,
                amount=locked_txn.amount,
                confirmed=True,
                status=Transaction.STATUS_COMPLETED,
                meta=reversal_meta,
            )

            locked_wallet.save(update_fields=["balance", "updated_at"])

            # Send signals
            balance_changed.send(
                sender=cls, wallet=locked_wallet, transaction=reversal_txn
            )
            transaction_created.send(sender=cls, transaction=reversal_txn)

            return reversal_txn

    @classmethod
    def expire_pending_transactions(cls, wallet, before_date=None):
        """
        Expire all pending transactions for a wallet before a given date.

        Args:
            wallet: The wallet to expire transactions for.
            before_date: Optional datetime; defaults to now.

        Returns:
            int: Number of transactions expired.
        """
        from django.utils import timezone

        if before_date is None:
            before_date = timezone.now()

        count = Transaction.objects.filter(
            wallet=wallet,
            status=Transaction.STATUS_PENDING,
            created_at__lt=before_date,
        ).update(status=Transaction.STATUS_EXPIRED)

        return count
