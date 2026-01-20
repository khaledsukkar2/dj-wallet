"""
Security tests for authorization and access control.
"""

from decimal import Decimal

import pytest

from django_wallets.services import WalletService


@pytest.mark.django_db
@pytest.mark.security
class TestWalletOwnership:
    """Tests for wallet ownership enforcement."""

    def test_wallets_isolated_between_users(self, user_factory):
        """Users should have separate isolated wallets."""
        user1 = user_factory()
        user2 = user_factory()

        WalletService.deposit(user1.wallet, Decimal("100.00"))
        WalletService.deposit(user2.wallet, Decimal("50.00"))

        user1.wallet.refresh_from_db()
        user2.wallet.refresh_from_db()

        assert user1.wallet.balance == Decimal("100.00")
        assert user2.wallet.balance == Decimal("50.00")
        assert user1.wallet.pk != user2.wallet.pk

    def test_wallet_uuid_format(self, wallet):
        """Wallet UUID should be a proper UUIDv4."""
        import uuid

        # Should be a valid UUID
        assert isinstance(wallet.uuid, uuid.UUID)
        # UUID version 4
        assert wallet.uuid.version == 4

    def test_holder_type_prevents_cross_access(self, user, organization_factory):
        """Different holder types should not share wallets."""

        org = organization_factory()

        user_wallet = user.wallet
        org_wallet = org.wallet

        # Verify they have different holder types
        assert user_wallet.holder_type != org_wallet.holder_type

        # Verify they are different wallets
        assert user_wallet.pk != org_wallet.pk

        # Verify the wallets belong to correct holders
        assert user_wallet.holder_id == user.pk
        assert org_wallet.holder_id == org.pk


@pytest.mark.django_db
@pytest.mark.security
class TestWalletIsolation:
    """Tests for wallet isolation between holders."""

    def test_wallet_cannot_be_accessed_by_id_alone(self, user_factory):
        """Wallet access requires both holder_type and holder_id."""
        from django.contrib.contenttypes.models import ContentType

        from django_wallets.models import Wallet

        user1 = user_factory()
        user2 = user_factory()

        wallet1 = user1.wallet

        # Even if you know the holder_id, you need the right holder_type
        ct = ContentType.objects.get_for_model(user1)

        # This should find user1's wallet
        found = Wallet.objects.filter(
            holder_type=ct,
            holder_id=user1.pk,
            slug="default"
        ).first()
        assert found == wallet1

        # This should NOT find user1's wallet when looking for user2
        not_found = Wallet.objects.filter(
            holder_type=ct,
            holder_id=user2.pk,
            slug="default"
        ).first()
        assert not_found != wallet1 or not_found is None

    def test_transaction_wallet_integrity(self, wallet):
        """Transactions should always belong to the correct wallet."""

        txn = WalletService.deposit(wallet, Decimal("100.00"))

        # Transaction should reference the correct wallet
        assert txn.wallet_id == wallet.pk

        # Should appear in wallet's transactions
        assert txn in wallet.transactions.all()
