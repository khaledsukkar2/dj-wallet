"""
Django signals for wallet events.

These signals allow you to hook into wallet operations
and react to balance changes and transaction events.
"""

from django.dispatch import Signal

# Emitted when a wallet's balance changes (after deposit/withdraw is confirmed)
# Sender: The service class that made the change
# Arguments: wallet, transaction
balance_changed = Signal()

# Emitted when a new transaction is created (regardless of confirmation status)
# Sender: The service class that created the transaction
# Arguments: transaction
transaction_created = Signal()

# Emitted when a new wallet is created
# Sender: The Wallet model class
# Arguments: wallet, holder
wallet_created = Signal()

# Emitted when a transfer is completed
# Sender: TransferService
# Arguments: transfer, from_wallet, to_wallet
transfer_completed = Signal()

# Emitted when a transaction is confirmed after being created as unconfirmed
# Sender: The service class that confirmed the transaction
# Arguments: transaction
transaction_confirmed = Signal()

# Emitted before a withdrawal (can be used for validation/blocking)
# Sender: WalletService
# Arguments: wallet, amount, meta
pre_withdraw = Signal()

# Emitted before a deposit (can be used for validation/blocking)
# Sender: WalletService
# Arguments: wallet, amount, meta
pre_deposit = Signal()
