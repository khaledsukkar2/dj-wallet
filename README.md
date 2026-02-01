# dj-wallets

[![PyPI version](https://badge.fury.io/py/dj-wallet.svg)](https://badge.fury.io/py/dj-wallet)
[![Python Versions](https://img.shields.io/pypi/pyversions/dj-wallet.svg)](https://pypi.org/project/dj-wallet/)
[![Django Versions](https://img.shields.io/pypi/djversions/dj-wallet.svg)](https://pypi.org/project/dj-wallet/)
[![License](https://img.shields.io/badge/license-MIT-purple)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-92%25-yellowgreen)](https://github.com/khaledsukkar2/dj-wallet)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/khaledsukkar2/dj-wallet)

A **secure**, **flexible**, and **powerful** virtual wallet system for Django applications.

*Inspired by [laravel-wallet](https://github.com/bavix/laravel-wallet)*

---

## What is a Virtual Wallet?

Think of this as a "digital bank account" inside your app. It doesn't handle real money directly (like Stripe or PayPal), but it keeps track of a **virtual balance** for your users.

- **Deposit**: Adds "money" to the user's balance.
- **Withdraw**: Takes "money" away from the balance.
- **Pay**: Automatically deducts the cost of an item from the user's wallet and (optionally) transfers it to the seller.
- **Safe**: Behind the scenes, the library ensures that two transactions can't happen at the exact same time to break the balance (Race Condition Protection).

---

## Features

- **Multi-Wallet Support**: Each user can have multiple wallets (default, savings, USD, etc.).
- **Atomic Transactions**: Ensures data integrity during concurrent operations.
- **Transfers & Exchanges**: Move funds between users or between different wallets of the same user.
- **Product Purchases**: Built-in support for purchasing items using wallet balance.
- **Polymorphic Holders**: Attach wallets to any Django model (Users, Organizations, Teams).

---

## Installation

```bash
pip install dj-wallet
```

Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'dj_wallet',
]
```

Run migrations:

```bash
python manage.py migrate
```

---

## Quick Start

### 1. Simple Setup
Add the `WalletMixin` to your custom User model to give it wallet capabilities.

```python
from django.contrib.auth.models import AbstractUser
from dj_wallet.mixins import WalletMixin

class User(WalletMixin, AbstractUser):
    pass
```

### 2. Standard Operations

```python
user = User.objects.create(username="khaled")

# Deposit: Adds to balance
user.deposit(500.00)

# Check balance
print(user.balance) # 500.00

# Withdraw: Deducts from balance
user.withdraw(100.00)

# Transfer: Deducts from one, adds to another
recipient = User.objects.create(username="friend")
user.transfer(recipient, 50.00)
```

---

## 🛒 Buying Things (`ProductMixin`)

The library includes a robust system for handling product purchases. To make any Django model "buyable," apply the `ProductMixin`. This allows wallets to interact directly with your business logic.

### 1. Implementation
To make an item purchasable, implement the `ProductMixin` in your model:

```python
from dj_wallet.mixins import ProductMixin
from django.db import models

class DigitalCourse(ProductMixin, models.Model):
    title = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_amount_product(self, customer):
        """REQUIRED: Return the price for this specific customer."""
        return self.price

    def can_buy(self, customer, quantity=1):
        """OPTIONAL: Check inventory or eligibility (default: True)."""
        return True

    def get_meta_product(self):
        """OPTIONAL: Add transaction metadata (default: {})."""
        return {"course_id": self.id}
```

### 2. Available Methods (ProductMixin)
These methods should be defined in your product class:

- **`get_amount_product(customer)`**: Returns the cost of the product. This is where you can implement dynamic pricing, discounts, or multi-currency logic.
- **`can_buy(customer, quantity)`**: Validation logic before purchase. Return `False` to block the transaction (e.g., if out of stock).
- **`get_meta_product()`**: Provide extra data that will be saved in the transaction's `meta` JSON field for auditing.

### 3. Processing a Purchase
A holder can pay for a product using the `.pay()` method.

```python
course = DigitalCourse.objects.get(id=1)

# This single line checks balance, validates availability, and transfers funds
try:
    transaction = user.pay(course)
    print("Course purchased successfully!")
except InsufficientFunds:
    print("Insufficient funds in wallet.")
except ProductNotAvailable:
    print("This item is currently out of stock.")
```

---

## Core Services

Django Wallets uses a component-based architecture where logic is encapsulated in services.

- **`WalletService`**: Base wallet operations (deposit, withdraw, reversals).
- **`TransferService`**: Fund movements between holders, refunds, and gifts.
- **`ExchangeService`**: Internal conversions between a holder's different wallets.
- **`PurchaseService`**: High-level logic for processing product payments.

---

## 🛠️ Available Methods Reference

### User/Holder Methods (via `WalletMixin`)
- **`.balance`**: Property that returns the current balance of the default wallet.
- **`.deposit(amount, meta=None, confirmed=True)`**: Adds funds to the default wallet. Supports metadata and unconfirmed states.
- **`.withdraw(amount, meta=None, confirmed=True)`**: Deducts funds. Raises `InsufficientFunds` if the balance is too low.
- **`.force_withdraw(amount)`**: Deducts funds regardless of balance (allows negative balance).
- **`.transfer(to_holder, amount)`**: Moves funds from this holder to another.
- **`.pay(product)`**: High-level method to purchase an item implementing `ProductMixin`.
- **`.get_wallet(slug)`**: Returns a specific wallet by name (creates it if it doesn't exist).
- **`.has_wallet(slug)`**: Checks if a wallet exists without creating it.
- **`.freeze_wallet(slug)`**: Locks a wallet from all incoming/outgoing transactions.
- **`.unfreeze_wallet(slug)`**: Re-enables a frozen wallet.
- **`.get_pending_transactions(slug)`**: Returns a QuerySet of transactions awaiting confirmation.

### 🏗️ Service Methods
For advanced usage, you can call services directly:

- **`WalletService.confirm_transaction(txn)`**: Moves a transaction from `PENDING` to `COMPLETED` and updates the wallet balance.
- **`WalletService.reverse_transaction(txn)`**: Perfectly undoes a transaction and records the reversal.
- **`TransferService.refund(transfer)`**: Reverses a transfer and returns money to the sender.
- **`ExchangeService.exchange(holder, from_slug, to_slug, amount)`**: Moves funds between two wallets owned by the same holder.

---

## Customization

### 1. Models
Extend the default models to add custom fields.

```python
from dj_wallet.abstract_models import AbstractWallet

class MyWallet(AbstractWallet):
    tax_exempt = models.BooleanField(default=False)

```

### 2. Mixins
Override existing logic or add helpers by extending the `WalletMixin`.

```python
from dj_wallet.mixins import WalletMixin

class MyCustomMixin(WalletMixin):
    def deposit(self, amount, meta=None, confirmed=True):
        print(f"User is depositing {amount}")
        return super().deposit(amount, meta, confirmed)

# settings.py
dj_wallet = {
    'WALLET_MIXIN_CLASS': 'myapp.mixins.MyCustomMixin',
}
```

### 3. Services
Override core business logic by extending the service classes.

```python
from dj_wallet.services.common import WalletService

class MyWalletService(WalletService):
    @classmethod
    def deposit(cls, wallet, amount, **kwargs):
        # Your custom logic here
        return super().deposit(wallet, amount, **kwargs)

# settings.py
dj_wallet = {
    'WALLET_SERVICE_CLASS': 'myapp.services.MyWalletService',
}
```

---

## Support Us

If you find this project useful, please consider supporting its development.

### Star the Repository
Show some love by [starring the project on GitHub](https://github.com/khaledsukkar2/django-wallets)!

### Sponsorship & Donations
- **BTC**: `13X8aZ23pFNCH2FPW6YpRTw4PGxo7AvFkN`
- **USDT (TRC20)**: `TEitNDQMm4upYmNvFeMpxTRGEJGdord3S5`
- **USDT (BEP20)**: `0xc491a2ba6f386ddbf26cdc906939230036473f5d`

---

## License

MIT License. See [LICENSE](LICENSE) for details.
