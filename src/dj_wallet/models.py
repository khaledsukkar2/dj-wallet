from django.db import models

from .abstract_models import AbstractTransaction, AbstractTransfer, AbstractWallet


class Wallet(AbstractWallet):
    """
    Concrete Wallet model.
    For custom wallet models, extend AbstractWallet instead.
    """


class Transaction(AbstractTransaction):
    """
    Concrete Transaction model.
    For custom transaction models, extend AbstractTransaction instead.
    """

    # The specific wallet this transaction affects
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions"
    )


class Transfer(AbstractTransfer):
    """
    Concrete Transfer model.
    For custom transfer models, extend AbstractTransfer instead.
    """

    # The transaction withdrawing money from sender
    withdraw = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="transfer_withdraw"
    )

    # The transaction depositing money to receiver
    deposit = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="transfer_deposit"
    )
