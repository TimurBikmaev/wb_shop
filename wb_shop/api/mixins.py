from rest_framework import serializers

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

    def get_item_total(self, obj):
        """Рассчитывает сумму каждой позиции."""
        return obj.product.price * obj.item_quantity


class TotalPriceSerializerMixin(serializers.ModelSerializer):
    """Считает общую сумму позиций товара для корзины и заказа."""
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        """Рассчитывает сумму всех позиций."""
        return CartOrderService.sum_items_total_price(obj.items.all())


class LookupMixin:
    """Поиск объектов по их публичному id."""
    lookup_field = 'public_id'
