"""
Integration tests for purchase workflows.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import InsufficientFunds, ProductEnded
from django_wallets.models import Transaction, Transfer
from django_wallets.services import PurchaseService, WalletService


@pytest.mark.django_db
@pytest.mark.integration
class TestPurchaseWorkflows:
    """Tests for complete purchase workflows."""

    def test_purchase_reduces_customer_balance(self, user, product):
        """Purchase should reduce customer balance by product price."""
        WalletService.deposit(user.wallet, Decimal("100.00"))

        PurchaseService.pay(user, product)

        user.wallet.refresh_from_db()
        # Product costs 25.00
        assert user.wallet.balance == Decimal("75.00")

    def test_purchase_without_product_wallet_burns_funds(self, user, product):
        """Purchase from product without wallet should withdraw (burn) funds."""
        WalletService.deposit(user.wallet, Decimal("100.00"))

        result = PurchaseService.pay(user, product)

        # Should return a Transaction (withdrawal), not a Transfer
        assert isinstance(result, Transaction)
        assert result.type == Transaction.TYPE_WITHDRAW

    def test_purchase_with_product_wallet_transfers(self, user, digital_product_factory):
        """Purchase from product with wallet should transfer to seller."""
        seller_product = digital_product_factory(price=Decimal("15.00"))

        WalletService.deposit(user.wallet, Decimal("100.00"))

        result = PurchaseService.pay(user, seller_product)

        # Should return a Transfer
        assert isinstance(result, Transfer)

        # Check seller received funds
        seller_product.wallet.refresh_from_db()
        assert seller_product.wallet.balance == Decimal("15.00")

    def test_purchase_out_of_stock(self, user, product_factory):
        """Purchase of out-of-stock product should raise ProductEnded."""
        product = product_factory(stock=0)
        WalletService.deposit(user.wallet, Decimal("100.00"))

        with pytest.raises(ProductEnded):
            PurchaseService.pay(user, product)

    def test_purchase_insufficient_funds(self, user, product_factory):
        """Purchase without sufficient funds should raise InsufficientFunds."""
        product = product_factory(price=Decimal("100.00"))
        WalletService.deposit(user.wallet, Decimal("50.00"))

        with pytest.raises(InsufficientFunds):
            PurchaseService.pay(user, product)

    def test_purchase_metadata_includes_product(self, user, product):
        """Purchase transaction should include product metadata."""
        WalletService.deposit(user.wallet, Decimal("100.00"))

        result = PurchaseService.pay(user, product)

        assert "product_id" in result.meta
        assert "product_name" in result.meta

    def test_purchase_multiple_quantities(self, user, product_factory):
        """Purchase with quantity should charge correct amount."""
        product = product_factory(price=Decimal("10.00"), stock=100)
        WalletService.deposit(user.wallet, Decimal("100.00"))

        PurchaseService.pay(user, product, quantity=3)

        user.wallet.refresh_from_db()
        # 3 * 10 = 30
        assert user.wallet.balance == Decimal("70.00")


@pytest.mark.django_db
@pytest.mark.integration
class TestMultiplePurchases:
    """Tests for multiple purchase scenarios."""

    def test_multiple_purchases_same_product(self, user, product):
        """Multiple purchases of same product should work."""
        WalletService.deposit(user.wallet, Decimal("100.00"))

        PurchaseService.pay(user, product)  # -25
        PurchaseService.pay(user, product)  # -25

        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("50.00")

    def test_multiple_purchases_different_products(self, user, product_factory):
        """Purchases of different products should work."""
        product1 = product_factory(price=Decimal("20.00"))
        product2 = product_factory(price=Decimal("15.00"))

        WalletService.deposit(user.wallet, Decimal("100.00"))

        PurchaseService.pay(user, product1)
        PurchaseService.pay(user, product2)

        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("65.00")

    def test_purchase_uses_mixin_pay_method(self, user, product):
        """User.pay() should work via WalletMixin."""
        WalletService.deposit(user.wallet, Decimal("100.00"))

        user.pay(product)

        user.wallet.refresh_from_db()
        assert user.wallet.balance == Decimal("75.00")
