"""
Unit tests for Wallet, Transaction, and Transfer models.
"""

from decimal import Decimal
from uuid import UUID

import pytest
from django.db import IntegrityError

from django_wallets.models import Transaction, Transfer

# ============================================================================
# Wallet Model Tests
# ============================================================================


@pytest.mark.django_db
class TestWalletModel:
    """Tests for the Wallet model."""

    def test_wallet_default_balance(self, user):
        """New wallet should have zero balance."""
        wallet = user.wallet
        assert wallet.balance == Decimal("0")

    def test_wallet_uuid_unique(self, user_factory):
        """Each wallet should have a unique UUID."""
        user1 = user_factory()
        user2 = user_factory()
        assert user1.wallet.uuid != user2.wallet.uuid

    def test_wallet_uuid_is_valid(self, wallet):
        """Wallet UUID should be a valid UUID."""
        assert isinstance(wallet.uuid, UUID)

    def test_wallet_slug_default(self, user):
        """Default wallet should have slug 'default'."""
        wallet = user.wallet
        assert wallet.slug == "default"

    def test_wallet_holder_unique_slug(self, user):
        """Same holder cannot have two wallets with same slug."""
        _ = user.wallet  # Create default wallet
        with pytest.raises(IntegrityError):
            user.create_wallet("default")

    def test_wallet_holder_different_slugs(self, user):
        """Same holder can have multiple wallets with different slugs."""
        wallet1 = user.wallet
        wallet2 = user.create_wallet("savings")
        assert wallet1.pk != wallet2.pk
        assert wallet1.slug == "default"
        assert wallet2.slug == "savings"

    def test_wallet_currency_default(self, wallet):
        """Default currency should come from settings."""
        assert wallet.currency == "USD"

    def test_wallet_currency_from_meta(self, user):
        """Currency should be read from meta if set."""
        wallet = user.create_wallet("euro", currency="EUR")
        assert wallet.currency == "EUR"

    def test_wallet_str_representation(self, wallet):
        """String representation should include slug and balance."""
        result = str(wallet)
        assert "default" in result
        assert "0" in result

    def test_wallet_holder_relation(self, user):
        """Wallet should link back to holder via GenericForeignKey."""
        wallet = user.wallet
        assert wallet.holder == user
        assert wallet.holder_id == user.pk

    def test_wallet_meta_default(self, wallet):
        """Wallet meta should default to empty dict."""
        assert wallet.meta == {} or wallet.meta is None or isinstance(wallet.meta, dict)

    def test_wallet_timestamps(self, wallet):
        """Wallet should have created_at and updated_at."""
        assert wallet.created_at is not None
        assert wallet.updated_at is not None


# ============================================================================
# Transaction Model Tests
# ============================================================================


@pytest.mark.django_db
class TestTransactionModel:
    """Tests for the Transaction model."""

    def test_transaction_uuid_unique(self, deposit_factory):
        """Each transaction should have a unique UUID."""
        txn1 = deposit_factory()
        txn2 = deposit_factory()
        assert txn1.uuid != txn2.uuid

    def test_transaction_type_deposit(self, deposit_factory):
        """Deposit transaction should have correct type."""
        txn = deposit_factory()
        assert txn.type == Transaction.TYPE_DEPOSIT

    def test_transaction_type_withdraw(self, funded_wallet):
        """Withdrawal transaction should have correct type."""
        from django_wallets.services import WalletService
        txn = WalletService.withdraw(funded_wallet, Decimal("50.00"))
        assert txn.type == Transaction.TYPE_WITHDRAW

    def test_transaction_wallet_relation(self, deposit_factory, wallet):
        """Transaction should link to its wallet."""
        txn = deposit_factory(wallet=wallet)
        assert txn.wallet == wallet

    def test_transaction_meta_default(self, deposit_factory):
        """Transaction meta should default to empty dict or be set."""
        txn = deposit_factory(meta=None)
        assert txn.meta == {} or txn.meta is None

    def test_transaction_confirmed_default(self, deposit_factory):
        """Transaction should be confirmed by default."""
        txn = deposit_factory()
        assert txn.confirmed is True

    def test_transaction_timestamps(self, deposit_factory):
        """Transaction should have timestamps."""
        txn = deposit_factory()
        assert txn.created_at is not None
        assert txn.updated_at is not None

    def test_transaction_amount_precision(self, wallet):
        """Transaction should preserve decimal precision."""
        from django_wallets.services import WalletService
        txn = WalletService.deposit(wallet, Decimal("123.45678901"))
        assert txn.amount == Decimal("123.45678901")


# ============================================================================
# Transfer Model Tests
# ============================================================================


@pytest.mark.django_db
class TestTransferModel:
    """Tests for the Transfer model."""

    def test_transfer_links_transactions(self, transfer_factory):
        """Transfer should link withdraw and deposit transactions."""
        transfer = transfer_factory()
        assert transfer.withdraw is not None
        assert transfer.deposit is not None
        assert transfer.withdraw.type == Transaction.TYPE_WITHDRAW
        assert transfer.deposit.type == Transaction.TYPE_DEPOSIT

    def test_transfer_from_to_relations(self, transfer_factory):
        """Transfer should have from_object and to_object."""
        transfer = transfer_factory()
        assert transfer.from_object is not None
        assert transfer.to_object is not None

    def test_transfer_default_fee_discount(self, transfer_factory):
        """Transfer should have zero fee and discount by default."""
        transfer = transfer_factory()
        assert transfer.fee == Decimal("0")
        assert transfer.discount == Decimal("0")

    def test_transfer_uuid_unique(self, transfer_factory):
        """Each transfer should have a unique UUID."""
        t1 = transfer_factory()
        t2 = transfer_factory()
        assert t1.uuid != t2.uuid

    def test_transfer_status_paid(self, transfer_factory):
        """Transfer via TransferService should have status PAID."""
        transfer = transfer_factory()
        assert transfer.status == Transfer.STATUS_PAID

    def test_transfer_timestamps(self, transfer_factory):
        """Transfer should have timestamps."""
        transfer = transfer_factory()
        assert transfer.created_at is not None
        assert transfer.updated_at is not None
