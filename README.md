# Django Wallets

[![PyPI version](https://badge.fury.io/py/django-wallets.svg)](https://badge.fury.io/py/django-wallets)
[![Python Versions](https://img.shields.io/pypi/pyversions/django-wallets.svg)](https://pypi.org/project/django-wallets/)
[![Django Versions](https://img.shields.io/pypi/djversions/django-wallets.svg)](https://pypi.org/project/django-wallets/)
[![License](https://img.shields.io/github/license/yourusername/django-wallets.svg)](https://github.com/yourusername/django-wallets/blob/main/LICENSE)
[![Tests](https://github.com/yourusername/django-wallets/workflows/Tests/badge.svg)](https://github.com/yourusername/django-wallets/actions)

A **secure**, **flexible**, and **easy-to-use** virtual wallet system for Django applications. Similar to [Laravel Wallet](https://github.com/bavix/laravel-wallet), but for Django!

## ✨ Features

- 🏦 **Multi-Wallet Support** - Each user can have multiple wallets (default, savings, USD, etc.)
- 💸 **Deposit & Withdrawal** - Atomic, transaction-safe operations
- 🔄 **Transfers** - Transfer funds between any wallet holders
- 💱 **Currency Exchange** - Exchange between wallets with custom rates
- 🛒 **Product Purchases** - Built-in support for purchasable items
- 🔒 **Secure by Default** - Row-level locking prevents race conditions
- 📊 **Full Audit Trail** - Every transaction is logged with metadata
- 🎯 **Polymorphic Holders** - Attach wallets to any Django model
- 📡 **Django Signals** - React to balance changes and transactions
- ⚡ **Optimistic Locking** - High-performance concurrent operations

## 📦 Installation

```bash
pip install django-wallets
```

Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'django_wallets',
]
```

Run migrations:

```bash
python manage.py migrate django_wallets
```

## 🚀 Quick Start

### 1. Add the mixin to your model

```python
from django.contrib.auth.models import AbstractUser
from django_wallets.mixins import WalletMixin

class User(WalletMixin, AbstractUser):
    pass
```

### 2. Perform wallet operations

```python
user = User.objects.get(pk=1)

# Deposit funds
user.deposit(100.00, meta={'source': 'bank_transfer'})

# Check balance
print(user.balance)  # Decimal('100.00')

# Withdraw funds
user.withdraw(25.00, meta={'reason': 'purchase'})

# Transfer to another user
recipient = User.objects.get(pk=2)
user.transfer(recipient, 50.00)
```

### 3. Multiple wallets

```python
# Create additional wallets
savings = user.create_wallet('savings', currency='USD')
crypto = user.create_wallet('crypto', currency='BTC')

# Deposit to specific wallet
from django_wallets.services import WalletService
WalletService.deposit(savings, 500.00)

# Exchange between wallets
from django_wallets.services import ExchangeService
ExchangeService.exchange(user, 'default', 'savings', 100.00, rate=1.0)
```

## 📖 Documentation

### Models

| Model | Description |
|-------|-------------|
| `Wallet` | A virtual wallet with balance, linked to any model |
| `Transaction` | An immutable record of a deposit or withdrawal |
| `Transfer` | A record linking two transactions for a transfer |

### Services

| Service | Description |
|---------|-------------|
| `WalletService` | Deposit, withdraw, force_withdraw operations |
| `TransferService` | Transfer funds between holders |
| `ExchangeService` | Exchange between wallets of same holder |
| `PurchaseService` | Purchase products with wallet balance |

### Mixins

| Mixin | Description |
|-------|-------------|
| `WalletMixin` | Add wallet capabilities to any model |
| `ProductMixin` | Make a model purchasable with wallet |

### Signals

```python
from django_wallets.signals import balance_changed, transaction_created

@receiver(balance_changed)
def on_balance_change(sender, wallet, transaction, **kwargs):
    print(f"Wallet {wallet.slug} new balance: {wallet.balance}")

@receiver(transaction_created)
def on_transaction(sender, transaction, **kwargs):
    print(f"New {transaction.type}: {transaction.amount}")
```

## ⚙️ Configuration

Add to your Django settings:

```python
DJANGO_WALLETS = {
    'TABLE_PREFIX': '',           # Prefix for database tables
    'MATH_SCALE': 8,              # Decimal precision
    'DEFAULT_CURRENCY': 'USD',    # Default currency code
}
```

## 🔧 Customization

django-wallets is designed to be fully customizable. You can extend models, override services, or create custom mixins.

### Custom Wallet Model

Extend the abstract base class to add custom fields:

```python
# myapp/models.py
from django_wallets.abstract_models import AbstractWallet

class CustomWallet(AbstractWallet):
    """Custom wallet with additional fields."""
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_frozen = models.BooleanField(default=False)
    
    class Meta(AbstractWallet.Meta):
        abstract = False
        db_table = 'custom_wallet'
```

### Custom Service

Create a custom service by extending the base class:

```python
# myapp/services.py
from django_wallets.services.common import WalletService
from django_wallets.exceptions import WalletException

class CustomWalletService(WalletService):
    """Custom service with modified validation."""
    
    @classmethod
    def deposit(cls, wallet, amount, meta=None, confirmed=True):
        # Custom logic: check if wallet is frozen
        if hasattr(wallet, 'is_frozen') and wallet.is_frozen:
            raise WalletException("Wallet is frozen")
        return super().deposit(wallet, amount, meta, confirmed)
```

Configure in settings:

```python
DJANGO_WALLETS = {
    'WALLET_SERVICE_CLASS': 'myapp.services.CustomWalletService',
}
```

### Custom Mixin

Create a custom mixin with additional methods:

```python
# myapp/mixins.py
from django_wallets.mixins import WalletMixin

class CustomWalletMixin(WalletMixin):
    """Mixin with additional wallet methods."""
    
    def has_sufficient_funds(self, amount):
        """Check if wallet has enough balance."""
        return self.balance >= amount
    
    def freeze_wallet(self):
        """Freeze the default wallet."""
        self.wallet.is_frozen = True
        self.wallet.save()
```

Configure in settings:

```python
DJANGO_WALLETS = {
    'WALLET_MIXIN_CLASS': 'myapp.mixins.CustomWalletMixin',
}
```

### Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TABLE_PREFIX` | `''` | Prefix for database table names |
| `MATH_SCALE` | `8` | Decimal precision for amounts |
| `DEFAULT_CURRENCY` | `'USD'` | Default currency code |
| `WALLET_SERVICE_CLASS` | `'django_wallets.services.common.WalletService'` | Custom wallet service |
| `TRANSFER_SERVICE_CLASS` | `'django_wallets.services.transfer.TransferService'` | Custom transfer service |
| `EXCHANGE_SERVICE_CLASS` | `'django_wallets.services.exchange.ExchangeService'` | Custom exchange service |
| `PURCHASE_SERVICE_CLASS` | `'django_wallets.services.purchase.PurchaseService'` | Custom purchase service |

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=django_wallets
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 💬 Support

- 📫 [GitHub Issues](https://github.com/yourusername/django-wallets/issues)
- 💬 [Discussions](https://github.com/yourusername/django-wallets/discussions)
