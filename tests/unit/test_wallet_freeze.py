"""
Tests for wallet freezing functionality.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import WalletFrozen
from django_wallets.services import WalletService


@pytest.mark.django_db
class TestWalletFreezing:
    """Tests for wallet freeze/unfreeze functionality."""

    def test_freeze_wallet(self, user):
        """Test that a wallet can be frozen."""
        wallet = user.wallet
        assert not wallet.is_frozen

        wallet.freeze(reason="Suspicious activity")

        wallet.refresh_from_db()
        assert wallet.is_frozen
        assert wallet.frozen_reason == "Suspicious activity"
        assert wallet.frozen_at is not None

    def test_unfreeze_wallet(self, user):
        """Test that a wallet can be unfrozen."""
        wallet = user.wallet
        wallet.freeze(reason="Test freeze")
        wallet.refresh_from_db()
        assert wallet.is_frozen

        wallet.unfreeze()

        wallet.refresh_from_db()
        assert not wallet.is_frozen
        assert wallet.frozen_reason == ""
        assert wallet.frozen_at is None

    def test_deposit_on_frozen_wallet_raises(self, user):
        """Test that depositing to a frozen wallet raises WalletFrozen."""
        wallet = user.wallet
        wallet.freeze(reason="Account suspended")
        wallet.refresh_from_db()

        with pytest.raises(WalletFrozen) as exc_info:
            WalletService.deposit(wallet, Decimal("100.00"))

        assert "frozen" in str(exc_info.value).lower()

    def test_withdraw_on_frozen_wallet_raises(self, funded_wallet):
        """Test that withdrawing from a frozen wallet raises WalletFrozen."""
        funded_wallet.freeze(reason="Fraud investigation")
        funded_wallet.refresh_from_db()

        with pytest.raises(WalletFrozen):
            WalletService.withdraw(funded_wallet, Decimal("50.00"))

    def test_force_withdraw_on_frozen_wallet_raises(self, funded_wallet):
        """Test that force_withdraw on a frozen wallet raises WalletFrozen."""
        funded_wallet.freeze(reason="Compliance hold")
        funded_wallet.refresh_from_db()

        with pytest.raises(WalletFrozen):
            WalletService.force_withdraw(funded_wallet, Decimal("50.00"))

    def test_freeze_via_mixin(self, user):
        """Test freeze/unfreeze via WalletMixin convenience methods."""
        user.freeze_wallet(reason="Security check")

        assert user.is_wallet_frozen()

        user.unfreeze_wallet()

        assert not user.is_wallet_frozen()

    def test_freeze_specific_wallet(self, user):
        """Test freezing a specific wallet by slug."""
        # Create multiple wallets
        user.create_wallet("savings")

        # Freeze only savings
        user.freeze_wallet("savings", reason="Audit required")

        # Default should not be frozen
        assert not user.is_wallet_frozen("default")
        # Savings should be frozen
        assert user.is_wallet_frozen("savings")

    def test_frozen_wallet_string_representation(self, user):
        """Test that frozen wallets show [FROZEN] in string representation."""
        wallet = user.wallet
        str_before = str(wallet)
        assert "[FROZEN]" not in str_before

        wallet.freeze()
        wallet.refresh_from_db()

        str_after = str(wallet)
        assert "[FROZEN]" in str_after


@pytest.mark.django_db
class TestBalanceRecalculation:
    """Tests for balance recalculation and audit functionality."""

    def test_recalculate_balance_matches_cached(self, funded_wallet):
        """Test that recalculated balance matches cached balance."""
        calculated, discrepancy = funded_wallet.recalculate_balance()

        assert calculated == funded_wallet.balance
        assert discrepancy == Decimal("0")

    def test_recalculate_after_multiple_transactions(self, user):
        """Test recalculation after multiple deposits and withdrawals."""
        wallet = user.wallet

        WalletService.deposit(wallet, Decimal("100.00"))
        WalletService.deposit(wallet, Decimal("50.00"))
        WalletService.withdraw(wallet, Decimal("30.00"))

        wallet.refresh_from_db()
        expected = Decimal("120.00")

        calculated, discrepancy = wallet.recalculate_balance()

        assert calculated == expected
        assert wallet.balance == expected
        assert discrepancy == Decimal("0")

    def test_sync_balance_corrects_discrepancy(self, funded_wallet):
        """Test that sync_balance corrects any discrepancy."""
        # Manually corrupt the balance (simulating a bug)
        from django_wallets.models import Wallet

        Wallet.objects.filter(pk=funded_wallet.pk).update(balance=Decimal("999.99"))
        funded_wallet.refresh_from_db()

        assert funded_wallet.balance == Decimal("999.99")

        # Sync should correct it
        corrected = funded_wallet.sync_balance()

        assert corrected == Decimal("100.00")
        funded_wallet.refresh_from_db()
        assert funded_wallet.balance == Decimal("100.00")

    def test_audit_balance_returns_full_audit(self, user):
        """Test that audit_balance returns comprehensive audit info."""
        wallet = user.wallet

        WalletService.deposit(wallet, Decimal("100.00"), meta={"source": "test"})
        WalletService.withdraw(wallet, Decimal("25.00"), meta={"reason": "purchase"})

        wallet.refresh_from_db()

        audit = wallet.audit_balance()

        assert audit["wallet_slug"] == "default"
        assert audit["cached_balance"] == Decimal("75.00")
        assert audit["calculated_balance"] == Decimal("75.00")
        assert audit["is_consistent"] is True
        assert audit["transaction_count"] == 2
        assert len(audit["transactions"]) == 2

    def test_audit_detects_inconsistency(self, funded_wallet):
        """Test that audit correctly identifies inconsistent balance."""
        # Manually corrupt the balance
        from django_wallets.models import Wallet

        Wallet.objects.filter(pk=funded_wallet.pk).update(balance=Decimal("50.00"))
        funded_wallet.refresh_from_db()

        audit = funded_wallet.audit_balance()

        assert audit["is_consistent"] is False
        assert audit["discrepancy"] == Decimal("-50.00")  # cached - calculated
