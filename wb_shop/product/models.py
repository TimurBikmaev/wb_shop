from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from core.constants import MoneyConstants, PublicIdConstants
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
        max_digits=MoneyConstants.MAX_DIGITS,
        decimal_places=MoneyConstants.DECIMAL_PLACES,
        validators=[MinValueValidator(MoneyConstants.PRICE_MIN_VALUE)],
    )
    warehouse_quantity = models.PositiveIntegerField(
        'На складе',
        validators=[MinValueValidator(ProductConstants.NOT_IN_WAREHOUSE)],
    )
    is_deleted = models.BooleanField('Удален ли', default=False)
    deleted_at = models.DateTimeField(
        'Дата удаления',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        db_table = 'product'
        ordering = ['name']

    def __str__(self) -> str:
        return f'Товар {self.public_id}'

    def __repr__(self) -> str:
        return f'<Product(id={self.id}, price={self.price})>'


class Cart(CreatedUpdatedMixin):
    """
    Покупная корзина пользователя.

    Хранит информацию о пользователе,
    дате создания и обновления корзины.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'
        db_table = 'cart'

    def __str__(self) -> str:
        return f'Корзина {self.user.email}'

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
    item_quantity = models.PositiveIntegerField(
        'Количество позиций',
        validators=[MinValueValidator(CartConstants.PRODUCTS_IN_CART_MIN)],
        default=CartConstants.PRODUCTS_IN_CART_MIN,
    )

    class Meta:
        db_table = 'cart_item'
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
        'Итоговая сумма',
        max_digits=MoneyConstants.MAX_DIGITS,
        decimal_places=MoneyConstants.DECIMAL_PLACES,
        validators=[MinValueValidator(MoneyConstants.PRICE_MIN_VALUE)],
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
        db_table = 'order'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Заказ {self.public_id}'

    def __repr__(self) -> str:
        return f'<Order(id={self.id}, user={self.user_id})>'


class OrderItem(models.Model):
    """
    Состав заказа из покупной корзины.

    Хранит информацию о заказе, продуктах, их публичном id,
    наименовании, количестве, цене и суммированной цене
    за позиции одного товара в момент заказа.

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
    public_id = models.CharField(
        'Public ID позиции',
        validators=[RegexValidator(PublicIdConstants.PUBLIC_ID_REGEX)],
        editable=False,
    )
    name = models.CharField(
        'Наименование в заказе',
        max_length=ProductConstants.NAME_MAX_LENGTH,
        editable=False,
    )
    item_quantity = models.PositiveIntegerField(
        'Количество позиций',
        validators=[MinValueValidator(OrderConstants.PRODUCTS_IN_ORDER_MIN)],
        editable=False,
    )
    item_price = models.DecimalField(
        'Цена в заказе',
        max_digits=MoneyConstants.MAX_DIGITS,
        decimal_places=MoneyConstants.DECIMAL_PLACES,
        validators=[MinValueValidator(MoneyConstants.PRICE_MIN_VALUE)],
        editable=False,
    )
    item_total = models.DecimalField(
        'Сумма позиций',
        max_digits=MoneyConstants.MAX_DIGITS,
        decimal_places=MoneyConstants.DECIMAL_PLACES,
        validators=[MinValueValidator(MoneyConstants.PRICE_MIN_VALUE)],
        editable=False,
    )

    class Meta:
        db_table = 'order_item'
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product'],
                name='unique_order_product',
            ),
        ]
        verbose_name_plural = 'Позиции заказа'

    def __str__(self) -> str:
        return f'Товар {self.public_id}'
