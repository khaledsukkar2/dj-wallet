"""
Test models for django_wallets testing.

These models demonstrate how to integrate django_wallets with your own models.
"""


from django.contrib.auth.models import AbstractUser
from django.db import models

from django_wallets.mixins import ProductMixin, WalletMixin


class User(WalletMixin, AbstractUser):
    """
    Custom user model with wallet capabilities.
    This demonstrates the basic integration of WalletMixin
    with Django's authentication system.
    """

    class Meta:
        app_label = "test_app"


class Organization(WalletMixin, models.Model):
    """
    Example of a non-user model with wallet capabilities.
    This demonstrates that wallets can be attached to any model,
    not just users.
    """

    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.name


class Product(ProductMixin, models.Model):
    """
    Example purchasable product model.
    This demonstrates the ProductMixin for items
    that can be purchased with wallet balance.
    """

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=100)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return f"{self.name} (${self.price})"

    def get_amount_product(self, customer):
        """Return the cost of the product."""
        return self.price

    def get_meta_product(self):
        """Return metadata for the transaction."""
        return {
            "product_id": self.pk,
            "product_name": self.name,
        }

    def can_buy(self, customer, quantity=1):
        """Check if the product is in stock."""
        return self.stock >= quantity


class DigitalProduct(ProductMixin, WalletMixin, models.Model):
    """
    Example of a product that also has a wallet to receive payments.
    This demonstrates a marketplace scenario where products
    receive payments into their own wallets (e.g., seller wallets).
    """

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.name

    def get_amount_product(self, customer):
        """Return the cost of the product."""
        return self.price

    def get_meta_product(self):
        """Return metadata for the transaction."""
        return {
            "product_id": self.pk,
            "product_name": self.name,
            "seller_id": self.seller_id,
        }

    def can_buy(self, customer, quantity=1):
        """Digital products are always available."""
        return True
