from django.contrib import admin
from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.constants import AdminConstants
from product.constants import ProductConstants
from product.models import Cart, CartItem, Order, OrderItem, Product


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = AdminConstants.NO_EXTRA


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = AdminConstants.NO_EXTRA
    readonly_fields = (
        'public_id',
        'name',
        'item_quantity',
        'item_price',
        'item_total',
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'price',
        'warehouse_quantity',
        'ordered_quantity',
        'is_deleted',
        'deleted_at',
        'updated_at',
        'created_at',
    )
    list_filter = (
        'is_deleted',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'name',
        'public_id',
        'description',
    )
    ordering = ('-created_at',)
    readonly_fields = ('ordered_quantity',)
    fieldsets = (
        ('Основное', {
            'fields': (
                'name',
                'description',
                'price',
                'warehouse_quantity',
            )
        }),
        ('Модерация', {
            'fields': (
                'is_deleted',
                'deleted_at',
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            ordered_quantity=Coalesce(
                Sum('order_items__item_quantity'),
                ProductConstants.NEVER_BOUGHT,
            )
        )

    @admin.display(description='Заказано', ordering='ordered_quantity')
    def ordered_quantity(self, obj):
        return obj.ordered_quantity


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = (
        'public_id',
        'user',
        'total_price',
        'status',
        'address',
        'created_at',
        'updated_at',
    )
    list_filter = (
        'status',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'public_id',
        'user__username',
        'user__email',
        'address',
    )
    ordering = ('-created_at',)
    readonly_fields = (
        'public_id',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        ('Основное', {
            'fields': (
                'user',
                'total_price',
                'status',
            )
        }),
        ('Доставка', {
            'fields': ('address',)
        }),
        ('Даты', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
