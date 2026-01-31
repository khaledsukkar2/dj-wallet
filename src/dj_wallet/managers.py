# dj_wallet/managers.py
from django.contrib.contenttypes.models import ContentType
from django.db import models


class WalletManager(models.Manager):
    def get_wallet(self, holder, slug="default", lock=False):
        """
        Retrieves a wallet for a holder, optionally locking the row.
        """
        ct = ContentType.objects.get_for_model(holder)
        queryset = self.get_queryset()

        if lock:
            queryset = queryset.select_for_update()

        # Return wallet or None if not created yet (creation usually handled by Mixin/Service)
        try:
            return queryset.get(holder_type=ct, holder_id=holder.pk, slug=slug)
        except self.model.DoesNotExist:
            return None


class TransactionManager(models.Manager):
    pass
