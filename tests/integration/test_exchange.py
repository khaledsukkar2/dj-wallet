"""
Integration tests for currency exchange workflows.
"""

from decimal import Decimal

import pytest

from django_wallets.exceptions import InsufficientFunds
from django_wallets.models import Transfer
from django_wallets.services import ExchangeService, WalletService


@pytest.mark.django_db()
@pytest.mark.integration()
class TestExchangeWorkflows:
    """Tests for currency exchange workflows."""

    def test_exchange_1_to_1_rate(self, user):
        """Exchange with 1:1 rate should transfer equal amounts."""
        # Create two wallets
        usd_wallet = user.wallet  # default
        eur_wallet = user.create_wallet("eur", currency="EUR")

        WalletService.deposit(usd_wallet, Decimal("100.00"))

        ExchangeService.exchange(
            user, "default", "eur", Decimal("50.00"), rate=Decimal("1.0")
        )

        usd_wallet.refresh_from_db()
        eur_wallet.refresh_from_db()

        assert usd_wallet.balance == Decimal("50.00")
        assert eur_wallet.balance == Decimal("50.00")

    def test_exchange_with_rate(self, user):
        """Exchange should apply conversion rate."""
        usd_wallet = user.wallet
        eur_wallet = user.create_wallet("eur")

        WalletService.deposit(usd_wallet, Decimal("100.00"))

        # 100 USD at 0.85 rate = 85 EUR
        ExchangeService.exchange(
            user, "default", "eur", Decimal("100.00"), rate=Decimal("0.85")
        )

        usd_wallet.refresh_from_db()
        eur_wallet.refresh_from_db()

        assert usd_wallet.balance == Decimal("0.00")
        assert eur_wallet.balance == Decimal("85.00")

    def test_exchange_rate_stored_in_meta(self, user):
        """Exchange rate should be stored in transaction metadata."""
        usd_wallet = user.wallet
        user.create_wallet("eur")

        WalletService.deposit(usd_wallet, Decimal("100.00"))

        txn = ExchangeService.exchange(
            user, "default", "eur", Decimal("50.00"), rate=Decimal("0.92")
        )

        assert "exchange_rate" in txn.meta
        assert txn.meta["exchange_rate"] == "0.92"

    def test_exchange_creates_transfer_record(self, user):
        """Exchange should create a Transfer with status=exchange."""
        usd_wallet = user.wallet
        user.create_wallet("eur")

        WalletService.deposit(usd_wallet, Decimal("100.00"))

        ExchangeService.exchange(user, "default", "eur", Decimal("50.00"))

        transfer = Transfer.objects.filter(status=Transfer.STATUS_EXCHANGE).first()
        assert transfer is not None

    def test_exchange_default_rate(self, user):
        """Exchange without rate should use 1.0."""
        usd_wallet = user.wallet
        eur_wallet = user.create_wallet("eur")

        WalletService.deposit(usd_wallet, Decimal("100.00"))

        ExchangeService.exchange(user, "default", "eur", Decimal("30.00"))

        eur_wallet.refresh_from_db()
        assert eur_wallet.balance == Decimal("30.00")

    def test_exchange_creates_target_wallet_if_needed(self, user):
        """Exchange should create target wallet via get_wallet."""
        WalletService.deposit(user.wallet, Decimal("100.00"))

        # Target wallet doesn't exist yet
        ExchangeService.exchange(user, "default", "new_wallet", Decimal("50.00"))

        # Should have been created
        new_wallet = user.get_wallet("new_wallet")
        assert new_wallet.balance == Decimal("50.00")


@pytest.mark.django_db()
@pytest.mark.integration()
class TestExchangeValidation:
    """Tests for exchange validation."""

    def test_exchange_insufficient_funds(self, user):
        """Exchange should fail if source wallet has insufficient funds."""
        usd_wallet = user.wallet
        user.create_wallet("eur")

        WalletService.deposit(usd_wallet, Decimal("50.00"))

        with pytest.raises(InsufficientFunds):
            ExchangeService.exchange(user, "default", "eur", Decimal("100.00"))

    def test_exchange_preserves_total_value(self, user):
        """Exchange at 1:1 should preserve total value."""
        wallet1 = user.wallet
        wallet2 = user.create_wallet("other")

        WalletService.deposit(wallet1, Decimal("100.00"))

        ExchangeService.exchange(user, "default", "other", Decimal("40.00"))

        wallet1.refresh_from_db()
        wallet2.refresh_from_db()

        total = wallet1.balance + wallet2.balance
        assert total == Decimal("100.00")
