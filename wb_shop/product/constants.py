from django.db.models import TextChoices


class CartConstants:
    DEFAULT_NAME = 'Основная'
    NAME_MAX_LENGTH = 100
    PRODUCTS_IN_CART_MIN = 1


class OrderConstants:
    ADDRESS_MAX_LENGTH = 255
    PRODUCTS_IN_ORDER_MIN = 1


class ProductConstants:
    DESCRIPTION_MAX_LENGTH = 1000
    NAME_MAX_LENGTH = 100
    NAME_SHORT = 20


class Status(TextChoices):
    cancelled = 'cancelled', 'Отменен'
    PENDING = 'pending', 'В ожидании'
    COMPLETED = 'completed', 'Завершен'
