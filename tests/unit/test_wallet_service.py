"""
Unit tests for WalletService.

Tests for amount validation, deposits, withdrawals, and force withdrawals.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import AmountInvalid, InsufficientFunds
from django_wallets.services import WalletService

# ============================================================================
# Amount Validation Tests
# ============================================================================


class TestVerifyAmount:
    """Tests for WalletService.verify_amount()."""

    def test_verify_amount_valid_decimal(self):
        """Valid Decimal should be accepted."""
        result = WalletService.verify_amount(Decimal("100.50"))
        assert result == Decimal("100.50")

    def test_verify_amount_valid_integer(self):
        """Valid integer should be converted to Decimal."""
        result = WalletService.verify_amount(100)
        assert result == Decimal("100")

    def test_verify_amount_valid_string(self):
        """Valid numeric string should be converted to Decimal."""
        result = WalletService.verify_amount("50.25")
        assert result == Decimal("50.25")

    def test_verify_amount_valid_float(self):
        """Float should be converted to Decimal via string to avoid precision issues."""
        result = WalletService.verify_amount(99.99)
        assert result == Decimal("99.99")

    def test_verify_amount_zero_rejected(self):
        """Zero amount should raise AmountInvalid."""
        with pytest.raises(AmountInvalid):
            WalletService.verify_amount(0)

    def test_verify_amount_negative_rejected(self):
        """Negative amount should raise AmountInvalid."""
        with pytest.raises(AmountInvalid):
            WalletService.verify_amount(-10)

    def test_verify_amount_invalid_string_rejected(self):
        """Non-numeric string should raise AmountInvalid."""
        with pytest.raises(AmountInvalid):
            WalletService.verify_amount("abc")

    def test_verify_amount_none_rejected(self):
        """None should raise AmountInvalid."""
        with pytest.raises(AmountInvalid):
            WalletService.verify_amount(None)

    def test_verify_amount_very_small(self):
        """Very small positive amount should be accepted."""
        result = WalletService.verify_amount(Decimal("0.00000001"))
        assert result == Decimal("0.00000001")

    def test_verify_amount_very_large(self):
        """Very large amount should be accepted."""
        large = Decimal("10") ** 50
        result = WalletService.verify_amount(large)
        assert result == large


# ============================================================================
# Deposit Tests
# ============================================================================


@pytest.mark.django_db
class TestDeposit:
    """Tests for WalletService.deposit()."""

    def test_deposit_increases_balance(self, wallet):
        """Deposit should increase wallet balance."""
        assert wallet.balance == Decimal("0")
        WalletService.deposit(wallet, Decimal("100.00"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.00")

    def test_deposit_cumulative(self, wallet):
        """Multiple deposits should accumulate."""
        WalletService.deposit(wallet, Decimal("50.00"))
        WalletService.deposit(wallet, Decimal("50.00"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.00")

    def test_deposit_creates_transaction(self, wallet):
        """Deposit should create a transaction record."""
        txn = WalletService.deposit(wallet, Decimal("100.00"))
        assert txn is not None
        assert txn.pk is not None

    def test_deposit_transaction_type(self, wallet):
        """Deposit transaction should have type 'deposit'."""
        from django_wallets.models import Transaction
        txn = WalletService.deposit(wallet, Decimal("100.00"))
        assert txn.type == Transaction.TYPE_DEPOSIT

    def test_deposit_with_metadata(self, wallet):
        """Deposit should store metadata."""
        meta = {"order_id": 123, "source": "payment_gateway"}
        txn = WalletService.deposit(wallet, Decimal("100.00"), meta=meta)
        assert txn.meta["order_id"] == 123
        assert txn.meta["source"] == "payment_gateway"

    def test_deposit_confirmed_true(self, wallet):
        """Confirmed deposit should update balance."""
        txn = WalletService.deposit(wallet, Decimal("100.00"), confirmed=True)
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("100.00")
        assert txn.confirmed is True

    def test_deposit_confirmed_false(self, wallet):
        """Unconfirmed deposit should NOT update balance."""
        txn = WalletService.deposit(wallet, Decimal("100.00"), confirmed=False)
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0")
        assert txn.confirmed is False

    def test_deposit_emits_balance_changed(self, wallet, signal_receiver):
        """Confirmed deposit should emit balance_changed signal."""
        from django_wallets.signals import balance_changed
        balance_changed.connect(signal_receiver)
        try:
            WalletService.deposit(wallet, Decimal("100.00"))
            assert signal_receiver.was_called
            assert "wallet" in signal_receiver.last_kwargs
            assert "transaction" in signal_receiver.last_kwargs
        finally:
            balance_changed.disconnect(signal_receiver)

    def test_deposit_emits_transaction_created(self, wallet, signal_receiver):
        """Deposit should emit transaction_created signal."""
        from django_wallets.signals import transaction_created
        transaction_created.connect(signal_receiver)
        try:
            WalletService.deposit(wallet, Decimal("100.00"))
            assert signal_receiver.was_called
            assert "transaction" in signal_receiver.last_kwargs
        finally:
            transaction_created.disconnect(signal_receiver)

    def test_deposit_unconfirmed_no_balance_signal(self, wallet, signal_receiver):
        """Unconfirmed deposit should NOT emit balance_changed."""
        from django_wallets.signals import balance_changed
        balance_changed.connect(signal_receiver)
        try:
            WalletService.deposit(wallet, Decimal("100.00"), confirmed=False)
            assert not signal_receiver.was_called
        finally:
            balance_changed.disconnect(signal_receiver)

    def test_deposit_decimal_precision(self, wallet):
        """Deposit should maintain decimal precision."""
        WalletService.deposit(wallet, Decimal("0.12345678"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0.12345678")


# ============================================================================
# Withdrawal Tests
# ============================================================================


@pytest.mark.django_db
class TestWithdraw:
    """Tests for WalletService.withdraw()."""

    def test_withdraw_decreases_balance(self, funded_wallet):
        """Withdrawal should decrease wallet balance."""
        WalletService.withdraw(funded_wallet, Decimal("40.00"))
        funded_wallet.refresh_from_db()
        assert funded_wallet.balance == Decimal("60.00")

    def test_withdraw_exact_balance(self, funded_wallet):
        """Withdrawing exact balance should leave zero."""
        WalletService.withdraw(funded_wallet, Decimal("100.00"))
        funded_wallet.refresh_from_db()
        assert funded_wallet.balance == Decimal("0")

    def test_withdraw_creates_transaction(self, funded_wallet):
        """Withdrawal should create a transaction record."""
        txn = WalletService.withdraw(funded_wallet, Decimal("50.00"))
        assert txn is not None
        assert txn.pk is not None

    def test_withdraw_transaction_type(self, funded_wallet):
        """Withdrawal transaction should have type 'withdraw'."""
        from django_wallets.models import Transaction
        txn = WalletService.withdraw(funded_wallet, Decimal("50.00"))
        assert txn.type == Transaction.TYPE_WITHDRAW

    def test_withdraw_insufficient_funds(self, funded_wallet):
        """Withdrawal exceeding balance should raise InsufficientFunds."""
        with pytest.raises(InsufficientFunds):
            WalletService.withdraw(funded_wallet, Decimal("150.00"))

    def test_withdraw_from_empty_wallet(self, wallet):
        """Withdrawal from empty wallet should raise InsufficientFunds."""
        with pytest.raises(InsufficientFunds):
            WalletService.withdraw(wallet, Decimal("1.00"))

    def test_withdraw_with_metadata(self, funded_wallet):
        """Withdrawal should store metadata."""
        meta = {"reason": "refund", "reference": "REF-123"}
        txn = WalletService.withdraw(funded_wallet, Decimal("50.00"), meta=meta)
        assert txn.meta["reason"] == "refund"
        assert txn.meta["reference"] == "REF-123"

    def test_withdraw_confirmed_false(self, funded_wallet):
        """Unconfirmed withdrawal should NOT update balance."""
        txn = WalletService.withdraw(funded_wallet, Decimal("50.00"), confirmed=False)
        funded_wallet.refresh_from_db()
        assert funded_wallet.balance == Decimal("100.00")
        assert txn.confirmed is False

    def test_withdraw_emits_signals(self, funded_wallet, signal_receiver):
        """Withdrawal should emit both signals."""
        from django_wallets.signals import balance_changed
        balance_changed.connect(signal_receiver)
        try:
            WalletService.withdraw(funded_wallet, Decimal("50.00"))
            assert signal_receiver.was_called
        finally:
            balance_changed.disconnect(signal_receiver)


# ============================================================================
# Force Withdrawal Tests
# ============================================================================


@pytest.mark.django_db
class TestForceWithdraw:
    """Tests for WalletService.force_withdraw()."""

    def test_force_withdraw_allows_negative(self, funded_wallet):
        """Force withdraw should allow negative balance."""
        WalletService.force_withdraw(funded_wallet, Decimal("150.00"))
        funded_wallet.refresh_from_db()
        assert funded_wallet.balance == Decimal("-50.00")

    def test_force_withdraw_from_empty(self, wallet):
        """Force withdraw from empty wallet should go negative."""
        WalletService.force_withdraw(wallet, Decimal("50.00"))
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("-50.00")

    def test_force_withdraw_creates_transaction(self, wallet):
        """Force withdraw should create a transaction."""
        txn = WalletService.force_withdraw(wallet, Decimal("100.00"))
        assert txn is not None
        assert txn.pk is not None

    def test_force_withdraw_emits_signals(self, wallet, signal_receiver):
        """Force withdraw should emit signals."""
        from django_wallets.signals import balance_changed
        balance_changed.connect(signal_receiver)
        try:
            WalletService.force_withdraw(wallet, Decimal("50.00"))
            assert signal_receiver.was_called
        finally:
            balance_changed.disconnect(signal_receiver)
