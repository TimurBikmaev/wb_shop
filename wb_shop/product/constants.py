from django.db.models import TextChoices


class CartConstants:
    DEFAULT_NAME = 'Основная'
    NAME_MAX_LENGTH = 100
    ONE_ITEM = 1
    PRODUCTS_IN_CART_MIN = 1


class OrderConstants:
    ADDRESS_MAX_LENGTH = 255
    ADDRESS_MIN_LENGTH = 3
    PRODUCTS_IN_ORDER_MIN = 1


class ProductConstants:
    DESCRIPTION_MAX_LENGTH = 1000
    DESCRIPTION_MIN_LENGTH = 10
    NAME_MAX_LENGTH = 100
    NAME_MIN_LENGTH = 2
    NAME_SHORT = 20
    NOT_IN_WAREHOUSE = 0


class Status(TextChoices):
    CANCELLED = 'cancelled', 'Отменен'
    PENDING = 'pending', 'В ожидании'
    COMPLETED = 'completed', 'Завершен'
