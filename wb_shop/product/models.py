from django.contrib.auth import get_user_model
from django.db import models

from core.constants import BalanceConstants
from core.mixins import CreatedUpdatedMixin, PublicIdMixin
from product.constants import OrderConstants, ProductConstants, Status


User = get_user_model()


class Product(PublicIdMixin, CreatedUpdatedMixin):
    """Модель товара"""
    name = models.CharField(
        'Название',
        max_length=ProductConstants.NAME_MAX_LENGTH,
        unique=True,
    )
    description = models.TextField(
        'Описание',
        max_length=ProductConstants.DESCRIPTION_MAX_LENGTH,
    )
    price = models.DecimalField(
        'Цена',
        max_digits=BalanceConstants.MAX_DIGITS,
        decimal_places=BalanceConstants.DECIMAL_PLACES,
    )
    quantity = models.PositiveIntegerField('Количество')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return f'{self.name[:ProductConstants.NAME_SHORT]} | {self.price}'

    def __repr__(self):
        return f'<Product(id={self.id}, price={self.price})>'


class Cart(PublicIdMixin, CreatedUpdatedMixin):
    """Модель корзины"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='carts',
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'

    def __str__(self):
        return f'Корзина {self.public_id} | {self.user.email}'

    def __repr__(self):
        return f'<Cart(id={self.id}, user={self.user_id})>'


class CartItem(CreatedUpdatedMixin):
    """Товар в составе корзины"""
    quantity = models.PositiveIntegerField('Количество')
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Товар',

    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_cart_product',
            ),
        ]


class Order(PublicIdMixin, CreatedUpdatedMixin):
    """Модель заказа"""
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        verbose_name='Пользователь',
    )
    total_price = models.DecimalField(
        'Сумма',
        max_digits=BalanceConstants.MAX_DIGITS,
        decimal_places=BalanceConstants.DECIMAL_PLACES,
    )
    address = models.CharField(
        'Адрес',
        max_length=OrderConstants.ADDRESS_MAX_LENGTH,
    )
    status = models.CharField(
        'Статус',
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ {self.public_id} | {self.total_price}'

    def __repr__(self):
        return f'<Order(id={self.id}, user={self.user_id})>'


class OrderItem(CreatedUpdatedMixin):
    """Товар в составе заказа"""
    quantity = models.PositiveIntegerField('Количество')
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Товар',
    )
    price = models.DecimalField(
        'Цена',
        max_digits=BalanceConstants.MAX_DIGITS,
        decimal_places=BalanceConstants.DECIMAL_PLACES,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product'],
                name='unique_order_product',
            ),
        ]
