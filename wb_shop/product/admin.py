from django.contrib import admin
from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.constants import AdminConstants
from core.mixins import AdminAddDeleteMixin
from product.constants import OrderConstants, ProductConstants
from product.models import Order, OrderItem, Product


class OrderItemInline(AdminAddDeleteMixin, admin.TabularInline):
    """Отображает позиции заказа."""

    model = OrderItem
    extra = AdminConstants.NO_EXTRA
    readonly_fields = (
        'public_id', 'name', 'item_price', 'item_quantity', 'item_total'
    )

    def has_change_permission(self, request, obj=None):
        """Запрещает изменение позиций заказа."""
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Настраивает отображение и управление товарами в админ-панели."""

    list_display = (
        'public_id', 'name', 'price', 'warehouse_quantity',
        'ordered_quantity', 'is_deleted',
        'deleted_at', 'updated_at', 'created_at',
    )
    list_filter = ('is_deleted', 'created_at', 'updated_at')
    search_fields = ('name', 'public_id', 'description')
    ordering = ('name',)
    readonly_fields = ('ordered_quantity',)
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'description', 'price', 'warehouse_quantity')
        }),
        ('Модерация', {'fields': ('is_deleted', 'deleted_at')}),
    )

    def get_queryset(self, request):
        """Возвращает товары с рассчитанным количеством проданных единиц."""
        return super().get_queryset(request).annotate(
            ordered_quantity=Coalesce(
                Sum('order_items__item_quantity'),
                ProductConstants.NEVER_BOUGHT,
            )
        )

    @admin.display(description='Заказано', ordering='ordered_quantity')
    def ordered_quantity(self, obj):
        """Возвращает общее количество заказанных единиц товара."""
        return obj.ordered_quantity


@admin.register(Order)
class OrderAdmin(AdminAddDeleteMixin, admin.ModelAdmin):
    """Настраивает отображение и управление заказами в админ-панели."""

    inlines = [OrderItemInline]
    list_display = (
        'public_id', 'user', 'total_products', 'total_price',
        'status', 'address', 'created_at', 'updated_at',
    )
    list_filter = ('status',  'created_at', 'updated_at',)
    search_fields = ('public_id', 'user__email', 'address',)
    ordering = ('-created_at',)
    readonly_fields = (
        'public_id', 'user', 'total_products', 'total_price',
        'address', 'created_at', 'updated_at',
    )
    fieldsets = (
        ('Основное', {'fields': ('user',  'total_products', 'total_price',)}),
        ('Статус', {'fields': ('status',)}),
        ('Доставка', {'fields': ('address',)}),
        ('Даты', {'fields': ('created_at', 'updated_at',)}),
    )

    def get_queryset(self, request):
        """Возвращает заказы с общим количеством товаров."""
        return super().get_queryset(request).select_related('user').annotate(
            total_products=Coalesce(
                Sum('items__item_quantity'),
                OrderConstants.NO_ITEMS,
            )
        )

    @admin.display(description='Кол-во товаров', ordering='total_products')
    def total_products(self, obj):
        """Возвращает общее количество товаров в заказе."""
        return obj.total_products
