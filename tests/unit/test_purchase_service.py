"""
Unit tests for PurchaseService.

Tests for purchasing products with wallet balance.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import InsufficientFunds, ProductNotAvailable
from django_wallets.services import PurchaseService, WalletService


@pytest.mark.django_db()
class TestPurchaseService:
    """Tests for PurchaseService.pay()."""

    def test_pay_basic_product(self, user_factory, product_factory):
        """Basic product purchase should deduct from wallet."""
        customer = user_factory()
        product = product_factory(price=Decimal("25.00"))

        WalletService.deposit(customer.wallet, Decimal("100.00"))

        PurchaseService.pay(customer, product)

        customer.wallet.refresh_from_db()
        assert customer.wallet.balance == Decimal("75.00")

    def test_pay_product_out_of_stock(self, user_factory, product_factory):
        """Purchasing out of stock product should raise ProductNotAvailable."""
        customer = user_factory()
        product = product_factory(stock=0)

        WalletService.deposit(customer.wallet, Decimal("100.00"))

        with pytest.raises(ProductNotAvailable):
            PurchaseService.pay(customer, product)

    def test_pay_insufficient_funds(self, user_factory, product_factory):
        """Purchasing with insufficient funds should raise InsufficientFunds."""
        customer = user_factory()
        product = product_factory(price=Decimal("100.00"))

        WalletService.deposit(customer.wallet, Decimal("50.00"))

        with pytest.raises(InsufficientFunds):
            PurchaseService.pay(customer, product)

    def test_pay_with_quantity(self, user_factory, product_factory):
        """Purchase with quantity should multiply cost."""
        customer = user_factory()
        product = product_factory(price=Decimal("10.00"), stock=10)

        WalletService.deposit(customer.wallet, Decimal("100.00"))

        PurchaseService.pay(customer, product, quantity=3)

        customer.wallet.refresh_from_db()
        assert customer.wallet.balance == Decimal("70.00")  # 100 - (10 * 3)

    def test_pay_digital_product_with_wallet(
        self, user_factory, digital_product_factory
    ):
        """Digital product with wallet should transfer to seller."""
        customer = user_factory()
        product = digital_product_factory(price=Decimal("15.00"))

        WalletService.deposit(customer.wallet, Decimal("100.00"))

        PurchaseService.pay(customer, product)

        customer.wallet.refresh_from_db()
        product.wallet.refresh_from_db()

        assert customer.wallet.balance == Decimal("85.00")
        assert product.wallet.balance == Decimal("15.00")

    def test_pay_returns_transaction(self, user_factory, product_factory):
        """Pay should return a transaction record."""
        customer = user_factory()
        product = product_factory(price=Decimal("25.00"))

        WalletService.deposit(customer.wallet, Decimal("100.00"))

        result = PurchaseService.pay(customer, product)

        assert result is not None
        assert result.pk is not None

    def test_pay_exact_balance(self, user_factory, product_factory):
        """Purchase with exact balance should leave wallet at zero."""
        customer = user_factory()
        product = product_factory(price=Decimal("100.00"))

        WalletService.deposit(customer.wallet, Decimal("100.00"))

        PurchaseService.pay(customer, product)

        customer.wallet.refresh_from_db()
        assert customer.wallet.balance == Decimal("0")

    def test_pay_includes_metadata(self, user_factory, product_factory):
        """Purchase should include product metadata in transaction."""
        customer = user_factory()
        product = product_factory(name="Test Product", price=Decimal("25.00"))

        WalletService.deposit(customer.wallet, Decimal("100.00"))

        result = PurchaseService.pay(customer, product)

        # For products without wallets, result is the withdraw transaction
        assert "product_name" in result.meta
        assert result.meta["product_name"] == "Test Product"
