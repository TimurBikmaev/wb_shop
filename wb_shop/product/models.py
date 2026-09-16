from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from core.constants import BalanceConstants
from core.mixins import CreatedUpdatedMixin, PublicIdMixin
from product.constants import (
    CartConstants,
    OrderConstants,
    ProductConstants,
    Status,
)


User = get_user_model()


class Product(PublicIdMixin, CreatedUpdatedMixin):
    """
    Товар в каталоге интернет-магазина.

    Хранит информацию о наименовании, описании, цене,
    количестве на складе, дате добавления и обновления товара.

    Предусмотрен soft delete: товар помечается удалённым
    с сохранением записи в БД и даты удаления.
    """
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
    is_deleted = models.BooleanField('Удален ли', default=False)
    deleted_at = models.DateTimeField(
        'Дата удаления',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self) -> str:
        return f'{self.name[:ProductConstants.NAME_SHORT]} | {self.price}'

    def __repr__(self) -> str:
        return f'<Product(id={self.id}, price={self.price})>'


class Cart(PublicIdMixin, CreatedUpdatedMixin):
    """
    Покупная корзина пользователя.

    Хранит информацию о пользователе, наименовании,
    дате создания и обновления корзины.

    Предусматривает возможность создания нескольких корзин.
    Пользователь не может дублировать названия корзин.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='carts',
        verbose_name='Пользователь'
    )
    name = models.CharField(
        'Название',
        max_length=CartConstants.NAME_MAX_LENGTH,
        default=CartConstants.DEFAULT_NAME,
    )

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_cart_user_name_product',
            ),
        ]

    def __str__(self) -> str:
        return f'Корзина {self.public_id} | {self.user.email}'

    def __repr__(self) -> str:
        return f'<Cart(id={self.id}, user={self.user_id})>'


class CartItem(models.Model):
    """
    Состав покупной корзины.

    Хранит информацию о корзине, продуктах и их количестве.
    В корзине нельзя дублировать продукты.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.RESTRICT,
        related_name='cart_items',
        verbose_name='Товар',
    )
    product_quantity = models.PositiveIntegerField(
        'Количество товара',
        validators=[MinValueValidator(CartConstants.PRODUCTS_IN_CART_MIN)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'],
                name='unique_cart_product',
            ),
        ]


class Order(PublicIdMixin, CreatedUpdatedMixin):
    """
    Заказ пользователя.

    Хранит информацию о пользователе, общей стоимости,
    адресе, статусе, дате создания и обновления заказа.

    По умолчанию заказы отсортированы от новых к старым.
    """
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

    def __str__(self) -> str:
        return f'Заказ {self.public_id} | {self.total_price}'

    def __repr__(self) -> str:
        return f'<Order(id={self.id}, user={self.user_id})>'


class OrderItem(models.Model):
    """
    Состав заказа из покупной корзины.

    Хранит информацию о заказе, продуктах,
    их количестве, наименовании и цене в момент заказа.
    При создании нового заказа делает снимок продуктов.

    В заказе нельзя дублировать продукты.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.RESTRICT,
        related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.RESTRICT,
        related_name='order_items',
        verbose_name='Товар',
    )
    product_quantity = models.PositiveIntegerField(
        'Количество',
        validators=[MinValueValidator(OrderConstants.PRODUCTS_IN_ORDER_MIN)]
    )
    product_name = models.CharField(
        'Наименование в заказе',
        max_length=ProductConstants.NAME_MAX_LENGTH,
    )
    product_price = models.DecimalField(
        'Цена в заказе',
        max_digits=BalanceConstants.MAX_DIGITS,
        decimal_places=BalanceConstants.DECIMAL_PLACES,
    )

    def save(self, *args, **kwargs):
        """
        При создании позиции заказа сохраняет
        наименование и цену продукта на момент оформления.
        """
        if self._state.adding and self.product:
            self.product_name = self.product.name
            self.product_price = self.product.price
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product'],
                name='unique_order_product',
            ),
        ]
