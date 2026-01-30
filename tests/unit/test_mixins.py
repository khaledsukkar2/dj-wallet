"""
Unit tests for WalletMixin and ProductMixin.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from django_wallets.exceptions import WalletException

# ============================================================================
# WalletMixin Tests
# ============================================================================


@pytest.mark.django_db()
class TestWalletMixin:
    """Tests for WalletMixin functionality."""

    def test_wallet_property_creates_default(self, user):
        """First access to .wallet should create default wallet."""
        from django_wallets.models import Wallet

        initial_count = Wallet.objects.count()
        wallet = user.wallet
        assert Wallet.objects.count() == initial_count + 1
        assert wallet.slug == "default"

    def test_wallet_property_idempotent(self, user):
        """Repeated access to .wallet should return same wallet."""
        wallet1 = user.wallet
        wallet2 = user.wallet
        assert wallet1.pk == wallet2.pk

    def test_balance_property(self, user):
        """balance property should return wallet balance."""
        from django_wallets.services import WalletService

        assert user.balance == Decimal("0")
        WalletService.deposit(user.wallet, Decimal("100.00"))
        # Need to refresh to see balance change through property
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("100.00")

    def test_get_wallet_creates_if_needed(self, user):
        """get_wallet should create wallet if it doesn't exist."""
        from django_wallets.models import Wallet

        initial_count = Wallet.objects.count()
        wallet = user.get_wallet("savings")
        assert Wallet.objects.count() == initial_count + 1
        assert wallet.slug == "savings"

    def test_get_wallet_returns_existing(self, user):
        """get_wallet should return existing wallet."""
        created = user.get_wallet("savings")
        retrieved = user.get_wallet("savings")
        assert created.pk == retrieved.pk

    def test_create_wallet_with_meta(self, user):
        """create_wallet should store metadata."""
        wallet = user.create_wallet(
            "usd", currency="USD", description="US Dollar wallet"
        )
        assert wallet.meta["currency"] == "USD"
        assert wallet.meta["description"] == "US Dollar wallet"

    def test_create_wallet_duplicate_slug_fails(self, user):
        """Creating wallet with duplicate slug should fail."""
        user.create_wallet("test")
        with pytest.raises(IntegrityError):
            user.create_wallet("test")

    def test_deposit_method(self, user):
        """deposit should increase balance."""
        user.deposit(Decimal("100.00"))
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("100.00")

    def test_deposit_with_meta(self, user):
        """deposit should accept metadata."""
        txn = user.deposit(Decimal("100.00"), meta={"source": "test"})
        assert txn.meta["source"] == "test"

    def test_withdraw_method(self, user):
        """withdraw should decrease balance."""
        user.deposit(Decimal("100.00"))
        user.withdraw(Decimal("30.00"))
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("70.00")

    def test_force_withdraw_method(self, user):
        """force_withdraw should allow negative balance."""
        user.force_withdraw(Decimal("50.00"))
        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("-50.00")

    def test_transfer_method(self, user_factory):
        """transfer should move funds between holders."""
        from django_wallets.services import WalletService

        sender = user_factory()
        recipient = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))
        sender.transfer(recipient, Decimal("40.00"))

        sender.wallet.refresh_from_db()
        recipient.wallet.refresh_from_db()

        assert sender.wallet.balance == Decimal("60.00")
        assert recipient.wallet.balance == Decimal("40.00")

    def test_safe_transfer_validates_receiver(self, user):
        """safe_transfer should raise if receiver has no wallet."""

        class NoWalletObject:
            pass

        user.deposit(Decimal("100.00"))
        with pytest.raises(WalletException):
            user.safe_transfer(NoWalletObject(), Decimal("50.00"))

    def test_safe_transfer_works_with_valid_receiver(self, user_factory):
        """safe_transfer should work with valid wallet holder."""
        from django_wallets.services import WalletService

        sender = user_factory()
        recipient = user_factory()

        WalletService.deposit(sender.wallet, Decimal("100.00"))
        transfer = sender.safe_transfer(recipient, Decimal("30.00"))

        assert transfer is not None

    def test_pay_method(self, user, product):
        """pay should purchase a product."""
        user.deposit(Decimal("100.00"))
        user.pay(product)
        user.wallet.refresh_from_db()
        # Product costs 25.00
        assert user.wallet.balance == Decimal("75.00")


# ============================================================================
# ProductMixin Tests
# ============================================================================


@pytest.mark.django_db()
class TestProductMixin:
    """Tests for ProductMixin functionality."""

    def test_get_amount_product(self, product):
        """get_amount_product should return product price."""

        class FakeCustomer:
            pass

        amount = product.get_amount_product(FakeCustomer())
        assert amount == Decimal("25.00")

    def test_can_buy_default_true(self, product):
        """can_buy should return True when stock available."""

        class FakeCustomer:
            pass

        assert product.can_buy(FakeCustomer()) is True

    def test_can_buy_out_of_stock(self, product_factory):
        """can_buy should return False when out of stock."""
        product = product_factory(stock=0)

        class FakeCustomer:
            pass

        assert product.can_buy(FakeCustomer()) is False

    def test_get_meta_product(self, product):
        """get_meta_product should return product metadata."""
        meta = product.get_meta_product()
        assert "product_id" in meta
        assert "product_name" in meta


# ============================================================================
# Multi-holder Tests
# ============================================================================


@pytest.mark.django_db()
class TestMultiHolderWallets:
    """Tests for wallets on different holder types."""

    def test_user_has_wallet(self, user):
        """User model should have wallet via mixin."""
        wallet = user.wallet
        assert wallet is not None
        assert wallet.holder == user

    def test_organization_has_wallet(self, organization_factory):
        """Organization model should have wallet via mixin."""
        org = organization_factory()
        wallet = org.wallet
        assert wallet is not None
        assert wallet.holder == org

    def test_wallets_isolated_by_holder_type(self, user, organization_factory):
        """Different holder types should have isolated wallets."""
        org = organization_factory()

        user_wallet = user.wallet
        org_wallet = org.wallet

        assert user_wallet.pk != org_wallet.pk
        assert user_wallet.holder_type != org_wallet.holder_type
