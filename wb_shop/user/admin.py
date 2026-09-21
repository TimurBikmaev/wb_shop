from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from core.constants import AdminConstants, MoneyConstants
from core.mixins import AdminAddDeleteMixin
from product.models import Order

User = get_user_model()


class OrderInline(AdminAddDeleteMixin, admin.TabularInline):
    model = Order
    extra = AdminConstants.NO_EXTRA
    readonly_fields = (
        'public_id', 'address', 'total_price',
        'created_at', 'updated_at'
    )


@admin.register(User)
class UserAdmin(AdminAddDeleteMixin, admin.ModelAdmin):
    """Настраивает отображение и управление пользователями."""
    inlines = [OrderInline]

    list_display = (
        'public_id', 'email', 'is_active', 'total_orders',
        'total_purchases', 'balance', 'created_at', 'updated_at',
    )
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('public_id', 'email')
    ordering = ('email',)
    readonly_fields = (
        'public_id', 'email', 'first_name',
        'balance', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Основное', {'fields': ('email', 'first_name', 'balance')}),
        ('Права доступа', {'fields': ('is_active',)}),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        """
        Возвращает пользователей с их общим
        количеством заказов и суммой покупок.
        """
        return super().get_queryset(request).annotate(
            total_orders=Count('orders'),
            total_purchases=Coalesce(
                Sum('orders__total_price'),
                Value(MoneyConstants.NO_MONEY),
                output_field=DecimalField(
                    max_digits=MoneyConstants.MAX_DIGITS,
                    decimal_places=MoneyConstants.DECIMAL_PLACES,
                ),
            ),
        )

    @admin.display(description='Кол-во заказов', ordering='total_orders')
    def total_orders(self, obj):
        """Возвращает общее количество заказов пользователя."""
        return obj.total_orders

    @admin.display(description='Сумма покупок', ordering='total_purchases')
    def total_purchases(self, obj):
        """Возвращает общую сумму покупок пользователя."""
        return obj.total_purchases
