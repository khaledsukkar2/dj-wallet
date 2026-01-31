# dj-wallets

[![PyPI version](https://badge.fury.io/py/dj-wallets.svg)](https://badge.fury.io/py/dj-wallets)
[![Python Versions](https://img.shields.io/pypi/pyversions/dj-wallets.svg)](https://pypi.org/project/dj-wallets/)
[![Django Versions](https://img.shields.io/pypi/djversions/dj-wallets.svg)](https://pypi.org/project/dj-wallets/)
[![License](https://img.shields.io/badge/license-MIT-purple)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-92%25-yellowgreen)](https://github.com/khaledsukkar2/django-wallets/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/khaledsukkar2/django-wallets/)

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

## Buying Things (`ProductMixin`)

To make an item "buyable," just add `ProductMixin` to its model. When a user pays for it, the price is automatically deducted from their wallet.

```python
from dj_wallet.mixins import ProductMixin
from django.db import models

class DigitalCourse(ProductMixin, models.Model):
    title = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_amount_product(self, customer):
        return self.price  # The price to deduct

# Usage:
course = DigitalCourse.objects.get(id=1)

# This single line checks the balance and deducts the money
if user.pay(course):
    print("Money deducted and course purchased!")
```

---

## Core Services

Django Wallets uses a component-based architecture where logic is encapsulated in services.

- **`WalletService`**: Base wallet operations (deposit, withdraw, reversals).
- **`TransferService`**: Fund movements between holders, refunds, and gifts.
- **`ExchangeService`**: Internal conversions between a holder's different wallets.
- **`PurchaseService`**: High-level logic for processing product payments.

---

## Available Methods Reference

### User/Holder Methods (via `WalletMixin`)
- `.balance`: Get default wallet balance.
- `.deposit(amount)`: Add funds.
- `.withdraw(amount)`: Remove funds.
- `.transfer(to_holder, amount)`: Transfer to another holder.
- `.pay(product)`: Deduct money for a product.
- `.get_wallet(slug)`: Get/Create a wallet by its name (slug).
- `.freeze_wallet(slug)` / `.unfreeze_wallet(slug)`: Lock/Unlock a wallet.

### Service Methods
- `WalletService.confirm_transaction(txn)`: Approve a pending transaction.
- `WalletService.reverse_transaction(txn)`: Undo a finished transaction.
- `TransferService.refund(transfer)`: Refund a specific transfer.
- `ExchangeService.exchange(holder, from, to, amount, rate)`: Move funds between wallets.

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
