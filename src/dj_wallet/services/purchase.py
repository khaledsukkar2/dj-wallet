# django_bavix_wallet/services/purchase.py
from ..exceptions import ProductNotAvailable
from .common import WalletService
from .transfer import TransferService


class PurchaseService:
    @staticmethod
    def pay(customer, product, quantity=1):
        """
        Customer pays for a product.
        """
        if not product.can_buy(customer, quantity):
            raise ProductNotAvailable("Product is not available.")

        cost = product.get_amount_product(customer) * quantity
        meta = product.get_meta_product()

        # We assume the product might have a wallet to receive funds,
        # or the funds just disappear (burn).
        # If the product owner has a wallet:
        if hasattr(product, "wallet"):
            return TransferService.transfer(customer, product, cost, meta)
        else:
            # Just withdraw (payment to system)
            return WalletService.withdraw(customer.wallet, cost, meta)
