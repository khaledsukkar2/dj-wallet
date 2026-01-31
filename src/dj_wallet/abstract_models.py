"""
Abstract base models for django-wallets.

These abstract models contain all the fields and logic for wallets, transactions, and transfers.
Developers can extend these to create custom models with additional fields or modified behavior.

Usage:
    from dj_wallet.abstract_models import AbstractWallet

    class CustomWallet(AbstractWallet):
        custom_field = models.CharField(max_length=100)

        class Meta(AbstractWallet.Meta):
            abstract = False
"""

import uuid
from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from .conf import wallet_settings
from .managers import TransactionManager, WalletManager


class AbstractWallet(models.Model):
    """
    Abstract base class for Wallet model.
    Extend this class to create a custom wallet model with additional fields.
    Remember to set ``abstract = False`` in your Meta class and update
    ``dj_wallet['WALLET_MODEL']`` setting.
    """

    # The owner of the wallet (User, Organization, etc.)
    holder_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="%(class)s_wallets"
    )
    holder_id = models.PositiveIntegerField()
    holder = GenericForeignKey("holder_type", "holder_id")

    # Slug allows multiple wallets per user (e.g., 'default', 'savings', 'usd')
    slug = models.SlugField(default="default", help_text=_("The name of the wallet"))

    # Unique identifier for API usage
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # The cached balance
    balance = models.DecimalField(
        max_digits=64,
        decimal_places=wallet_settings.WALLET_MATH_SCALE,
        default=Decimal("0.00"),
    )

    # Configuration for this specific wallet
    decimal_places = models.PositiveSmallIntegerField(
        default=wallet_settings.WALLET_MATH_SCALE
    )

    # Wallet freeze status
    is_frozen = models.BooleanField(
        default=False, help_text=_("Whether the wallet is frozen")
    )
    frozen_at = models.DateTimeField(
        null=True, blank=True, help_text=_("When the wallet was frozen")
    )
    frozen_reason = models.CharField(
        max_length=255, blank=True, help_text=_("Reason for freezing")
    )

    # Metadata for the wallet
    meta = models.JSONField(blank=True, null=True, default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WalletManager()

    class Meta:
        abstract = True
        unique_together = (("holder_type", "holder_id", "slug"),)
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")

    def __str__(self):
        frozen_indicator = " [FROZEN]" if self.is_frozen else ""
        return f"{self.slug} ({self.balance}){frozen_indicator}"

    @property
    def currency(self):
        return self.meta.get("currency", wallet_settings.WALLET_DEFAULT_CURRENCY)

    def freeze(self, reason=""):
        """
        Freeze the wallet to prevent all transactions.

        Args:
            reason: Optional reason for freezing the wallet.
        """
        from django.utils import timezone

        self.is_frozen = True
        self.frozen_at = timezone.now()
        self.frozen_reason = reason
        self.save(
            update_fields=["is_frozen", "frozen_at", "frozen_reason", "updated_at"]
        )

    def unfreeze(self):
        """Unfreeze the wallet to allow transactions."""
        self.is_frozen = False
        self.frozen_at = None
        self.frozen_reason = ""
        self.save(
            update_fields=["is_frozen", "frozen_at", "frozen_reason", "updated_at"]
        )

    def recalculate_balance(self):
        """
        Recalculate balance from confirmed transactions.

        Returns:
            tuple: (calculated_balance, discrepancy) where discrepancy is
                   the difference between cached and calculated balance.
        """
        from decimal import Decimal

        from django.db.models import Case, F, Sum, Value, When

        # Get all confirmed transactions for this wallet
        result = self.transactions.filter(confirmed=True).aggregate(
            deposits=Sum(
                Case(
                    When(type="deposit", then=F("amount")),
                    default=Value(Decimal("0")),
                )
            ),
            withdrawals=Sum(
                Case(
                    When(type="withdraw", then=F("amount")),
                    default=Value(Decimal("0")),
                )
            ),
        )

        deposits = result["deposits"] or Decimal("0")
        withdrawals = result["withdrawals"] or Decimal("0")
        calculated_balance = deposits - withdrawals
        discrepancy = self.balance - calculated_balance

        return calculated_balance, discrepancy

    def sync_balance(self):
        """
        Sync the cached balance with the calculated balance from transactions.

        Returns:
            Decimal: The corrected balance.
        """
        calculated_balance, _ = self.recalculate_balance()
        if self.balance != calculated_balance:
            self.balance = calculated_balance
            self.save(update_fields=["balance", "updated_at"])
        return self.balance

    def audit_balance(self):
        """
        Get a detailed audit trail of all transactions affecting this wallet.

        Returns:
            dict: Audit information including transactions and balance verification.
        """
        transactions = list(
            self.transactions.all()
            .order_by("created_at")
            .values("uuid", "type", "amount", "confirmed", "created_at", "meta")
        )

        calculated_balance, discrepancy = self.recalculate_balance()

        return {
            "wallet_uuid": str(self.uuid),
            "wallet_slug": self.slug,
            "cached_balance": self.balance,
            "calculated_balance": calculated_balance,
            "discrepancy": discrepancy,
            "is_consistent": discrepancy == Decimal("0"),
            "transaction_count": len(transactions),
            "transactions": transactions,
        }


class AbstractTransaction(models.Model):
    """
    Abstract base class for Transaction model.
    Extend this class to create a custom transaction model with additional fields.
    """

    TYPE_DEPOSIT = "deposit"
    TYPE_WITHDRAW = "withdraw"

    TYPE_CHOICES = (
        (TYPE_DEPOSIT, _("Deposit")),
        (TYPE_WITHDRAW, _("Withdraw")),
    )

    # Transaction status constants
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REVERSED = "reversed"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = (
        (STATUS_PENDING, _("Pending")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_FAILED, _("Failed")),
        (STATUS_REVERSED, _("Reversed")),
        (STATUS_EXPIRED, _("Expired")),
    )

    # The entity causing the transaction
    payable_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="%(class)s_transactions"
    )
    payable_id = models.PositiveIntegerField()
    payable = GenericForeignKey("payable_type", "payable_id")

    # Note: wallet FK is defined in concrete class to allow custom wallet model

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=64, decimal_places=wallet_settings.WALLET_MATH_SCALE
    )
    confirmed = models.BooleanField(default=True)

    # Transaction status for workflow management
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_COMPLETED,
        help_text=_("Current status of the transaction"),
    )

    meta = models.JSONField(blank=True, null=True, default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TransactionManager()

    class Meta:
        abstract = True

    def __str__(self):
        status_indicator = (
            f" [{self.status.upper()}]" if self.status != self.STATUS_COMPLETED else ""
        )
        return f"{self.type} {self.amount}{status_indicator}"

    @property
    def is_pending(self):
        """Check if transaction is pending confirmation."""
        return self.status == self.STATUS_PENDING

    @property
    def is_completed(self):
        """Check if transaction is completed."""
        return self.status == self.STATUS_COMPLETED

    @property
    def is_reversible(self):
        """Check if transaction can be reversed."""
        return self.status == self.STATUS_COMPLETED


class AbstractTransfer(models.Model):
    """
    Abstract base class for Transfer model.
    Extend this class to create a custom transfer model with additional fields.
    """

    STATUS_EXCHANGE = "exchange"
    STATUS_TRANSFER = "transfer"
    STATUS_PAID = "paid"
    STATUS_REFUND = "refund"
    STATUS_GIFT = "gift"

    STATUS_CHOICES = (
        (STATUS_EXCHANGE, _("Exchange")),
        (STATUS_TRANSFER, _("Transfer")),
        (STATUS_PAID, _("Paid")),
        (STATUS_REFUND, _("Refund")),
        (STATUS_GIFT, _("Gift")),
    )

    # Sender (Polymorphic)
    from_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="%(class)s_transfers_sent"
    )
    from_id = models.PositiveIntegerField()
    from_object = GenericForeignKey("from_type", "from_id")

    # Receiver
    to_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="%(class)s_transfers_received",
    )
    to_id = models.PositiveIntegerField()
    to_object = GenericForeignKey("to_type", "to_id")

    # Note: withdraw/deposit FKs defined in concrete class to allow custom transaction model

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_TRANSFER
    )

    discount = models.DecimalField(
        max_digits=64, decimal_places=wallet_settings.WALLET_MATH_SCALE, default=0
    )
    fee = models.DecimalField(
        max_digits=64, decimal_places=wallet_settings.WALLET_MATH_SCALE, default=0
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"Transfer {self.status} ({self.uuid})"
