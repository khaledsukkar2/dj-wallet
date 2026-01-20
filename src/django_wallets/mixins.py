from django.contrib.contenttypes.models import ContentType

from .exceptions import WalletException
from .models import Wallet


class WalletMixin:
    """
    Mixin to give a model wallet capabilities.
    Add this mixin to any Django model to enable wallet functionality:
        class User(WalletMixin, AbstractUser):
            pass
    For customization, extend this class and set WALLET_MIXIN_CLASS in settings.
    """

    @property
    def balance(self):
        """Returns the balance of the default wallet."""
        return self.wallet.balance

    @property
    def wallet(self):
        """
        Returns the default wallet, creating it if necessary.
        Uses get_or_create to ensure existence.
        """
        ct = ContentType.objects.get_for_model(self)
        w, created = Wallet.objects.get_or_create(
            holder_type=ct, holder_id=self.pk, slug="default"
        )
        return w

    def get_wallet(self, slug="default"):
        """
        Retrieve a specific wallet by slug.
        """
        ct = ContentType.objects.get_for_model(self)
        w, _ = Wallet.objects.get_or_create(
            holder_type=ct, holder_id=self.pk, slug=slug
        )
        return w

    def create_wallet(self, slug, **meta):
        """
        Explicitly create a wallet with metadata.
        """
        ct = ContentType.objects.get_for_model(self)
        return Wallet.objects.create(
            holder_type=ct, holder_id=self.pk, slug=slug, meta=meta
        )

    def deposit(self, amount, meta=None, confirmed=True):
        """Proxy to WalletService deposit"""
        from .utils import get_wallet_service
        WalletService = get_wallet_service()
        return WalletService.deposit(self.wallet, amount, meta, confirmed)

    def withdraw(self, amount, meta=None, confirmed=True):
        """Proxy to WalletService withdraw"""
        from .utils import get_wallet_service
        WalletService = get_wallet_service()
        return WalletService.withdraw(self.wallet, amount, meta, confirmed)

    def force_withdraw(self, amount, meta=None, confirmed=True):
        """Proxy to WalletService force_withdraw"""
        from .utils import get_wallet_service
        WalletService = get_wallet_service()
        return WalletService.force_withdraw(self.wallet, amount, meta, confirmed)

    def transfer(self, to_holder, amount, meta=None):
        """
        Transfer funds to another holder.
        """
        from .utils import get_transfer_service
        TransferService = get_transfer_service()
        return TransferService.transfer(self, to_holder, amount, meta)

    def safe_transfer(self, to_holder, amount, meta=None):
        """
        Transfer with additional checks (e.g. check if receiver exists).
        """
        if not hasattr(to_holder, "wallet"):
            raise WalletException("Receiver does not have a wallet.")
        return self.transfer(to_holder, amount, meta)

    def pay(self, item):
        """
        Pay for an item (ProductLimitedInterface).
        """
        from .utils import get_purchase_service
        PurchaseService = get_purchase_service()
        return PurchaseService.pay(self, item)


class ProductMixin:
    """
    Interface for items that can be purchased via wallet.
    Implement this mixin on purchasable product models:
        class Product(ProductMixin, models.Model):
            price = models.DecimalField(...)
            def get_amount_product(self, customer):
                return self.price
    """

    def get_amount_product(self, customer):
        """Return the cost of the product for the specific customer."""
        raise NotImplementedError("Subclasses must implement get_amount_product()")

    def get_meta_product(self):
        """Return metadata for the transaction."""
        return {}

    def can_buy(self, customer, quantity=1):
        """
        Check if the product is in stock and available.
        Can be overridden for inventory logic.
        """
        return True


# Backwards compatibility alias
HasWalletMixin = WalletMixin
