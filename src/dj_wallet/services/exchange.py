# django_bavix_wallet/services/exchange.py
from decimal import Decimal

from django.db import transaction

from ..models import Transfer
from .common import WalletService


class ExchangeService:
    @staticmethod
    def exchange(holder, from_slug, to_slug, amount, rate=None):
        """
        Moves funds from one wallet to another belonging to the same holder, applying a rate.
        If rate is None, it implies 1:1 or requires an external lookup service.
        """
        from_wallet = holder.get_wallet(from_slug)
        to_wallet = holder.get_wallet(to_slug)

        if rate is None:
            # Default to 1.0 if not provided, or raise error depending on policy
            rate = Decimal("1.0")

        amount = Decimal(amount)
        converted_amount = amount * Decimal(rate)

        with transaction.atomic():
            # Withdraw from source
            withdraw_txn = WalletService.withdraw(
                from_wallet,
                amount,
                meta={"exchange_rate": str(rate), "target": to_slug},
            )

            # Deposit to target
            deposit_txn = WalletService.deposit(
                to_wallet,
                converted_amount,
                meta={"exchange_rate": str(rate), "source": from_slug},
            )

            # Record the exchange
            Transfer.objects.create(
                from_object=from_wallet,
                to_object=to_wallet,
                withdraw=withdraw_txn,
                deposit=deposit_txn,
                status=Transfer.STATUS_EXCHANGE,
                fee=0,
            )
            return deposit_txn
