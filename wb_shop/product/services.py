import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from core.constants import MoneyConstants
from product.models import Cart, CartItem, Order, OrderItem, Product

logger = logging.getLogger(__name__)


class CartOrderService:
    """Обработка операций для корзины и заказов."""
    @staticmethod
    def get_cart(user):
        """Возвращает корзину пользователя."""
        return get_object_or_404(
            Cart.objects.prefetch_related(
                Prefetch(
                    'items',
                    queryset=CartItem.objects.select_related('product')
                )
            ),
            user=user
        )

    @staticmethod
    def get_cart_item(user, product_public_id: str) -> tuple:
        """Проверяет и возвращает корзину, товар и его позицию в корзине.."""
        cart = get_object_or_404(Cart, user=user)
        product = get_object_or_404(Product, public_id=product_public_id)
        item = get_object_or_404(CartItem, cart=cart, product=product)

        return cart, product, item

    @staticmethod
    def sum_items_total_price(cart_items: list) -> Decimal:
        """Рассчитывает общую сумму позиций."""
        return sum(
            (
                item.product.price * item.item_quantity
                for item in cart_items
            ),
            MoneyConstants.NO_MONEY,
        )

    @staticmethod
    @transaction.atomic
    def create_order_from_cart(user, address: str):
        """
        Создает заказ на основе корзины.

        Фиксирует суммарную цену каждой позиции.
        Также фиксирует общую сумму всех позиций.

        Снимает деньги с баланса пользователя.
        """
        cart = CartOrderService.get_cart(user)
        cart_items = list(cart.items.all())

        CartOrderService.check_cart_items_and_reduce_quantity(cart_items)

        total_price = CartOrderService.sum_items_total_price(cart_items)
        if user.balance < total_price:
            gap = total_price - user.balance
            raise ValidationError(
                f'На балансе не хватает {gap} рублей для покупки. '
                'Отправьте POST-запрос на users/me/balance/.'
            )

        order = Order.objects.create(
            user=user,
            address=address,
            total_price=total_price
        )

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=item.product,
                public_id=item.product.public_id,
                name=item.product.name,
                item_quantity=item.item_quantity,
                item_price=item.product.price,
                item_total=item.item_quantity * item.product.price
            )
            for item in cart_items
        ])

        Product.objects.bulk_update(
            [item.product for item in cart_items],
            ['warehouse_quantity'],

        )

        cart.items.all().delete()

        user.balance -= total_price
        user.save(update_fields=['balance'])

        logger.info(
            'Создан заказ %s пользователем %s',
            order.public_id,
            user.public_id,
        )

        return order

    @staticmethod
    def check_cart_items_and_reduce_quantity(cart_items: list) -> None:
        """
        Проверяет статус удаления товаров,
        а также их наличие в корзине и на складе.
        Уменьшает остатки в объектах Product.
        """
        if not cart_items:
            raise ValidationError('Корзина пуста.')

        for item in cart_items:

            if item.product.is_deleted is True:
                raise ValidationError(
                    f'Товар \'{item.product.public_id}\' удален из магазина. '
                    f'Отправьте DELETE-запрос на cart/item/public_id/.'
                )

            if item.product.warehouse_quantity < item.item_quantity:
                gap = item.item_quantity - item.product.warehouse_quantity
                raise ValidationError(
                    f'На складе не хватает {gap} товаров '
                    f'\'{item.product.public_id}\'. Отправьте '
                    'PATCH или DELETE запрос на cart/item/public_id/.'
                )

            item.product.warehouse_quantity -= item.item_quantity
