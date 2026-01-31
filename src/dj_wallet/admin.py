# dj_wallet/admin.py
from django.contrib import admin

from .models import Transaction, Transfer, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("slug", "holder", "balance", "created_at")
    search_fields = ("slug", "uuid")
    readonly_fields = (
        "balance",
        "uuid",
    )  # Balance should not be edited manually to preserve audit trail

    # Helper to show holder in list regardless of type
    def holder(self, obj):
        return f"{obj.holder_type} - {obj.holder_id}"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("uuid", "wallet", "type", "amount", "confirmed", "created_at")
    list_filter = ("type", "confirmed", "created_at")
    search_fields = ("uuid", "wallet__slug")


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("uuid", "from_object", "to_object", "status", "created_at")
