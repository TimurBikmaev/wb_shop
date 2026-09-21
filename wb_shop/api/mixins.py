from decimal import Decimal

from rest_framework import serializers

from core.constants import MoneyConstants
from product.services import CartOrderService


class ExcudeNoneSerializerMixin(serializers.ModelSerializer):
    """Исключаются null-поля."""

    def to_representation(self, obj):
        """Исключение null-полей и пустых строк из ответа сериализатора."""
        data = super().to_representation(obj)
        return {
            attr: value for attr, value in data.items()
            if value is not None and value != ''
        }


class ItemTotalSerializerMixin(serializers.ModelSerializer):
    """Считает сумму позиций товара для корзины и заказа."""
    item_total = serializers.SerializerMethodField()

    def get_item_total(self, obj) -> Decimal:
        """Рассчитывает сумму каждой позиции."""
        return obj.product.price * obj.item_quantity


class TotalPriceSerializerMixin(serializers.ModelSerializer):
    """Считает общую сумму позиций товара для корзины и заказа."""
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj) -> Decimal:
        """Рассчитывает сумму всех позиций."""
        return CartOrderService.sum_items_total_price(obj.items.all())


class TotalOrderPurchaseMixin(serializers.ModelSerializer):
    total_orders = serializers.IntegerField()
    total_purchases = serializers.DecimalField(
        max_digits=MoneyConstants.MAX_DIGITS,
        decimal_places=MoneyConstants.DECIMAL_PLACES,
    )


class HttpLookupMixin:
    """
    Поиск объектов по их публичному id.
    Доступ ко всем HTTP-методам кроме PUT.
    """
    lookup_field = 'public_id'
    http_method_names = ['get', 'post', 'patch', 'delete']
