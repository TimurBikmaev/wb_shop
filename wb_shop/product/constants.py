from django.db.models import TextChoices


class OrderConstants:
    ADDRESS_MAX_LENGTH = 255


class ProductConstants:
    DESCRIPTION_MAX_LENGTH = 1000
    NAME_MAX_LENGTH = 100
    NAME_SHORT = 20


class Status(TextChoices):
    REJECTED = 'rejected', 'Отменен'
    PENDING = 'pending', 'В ожидании'
    COMPLETED = 'completed', 'Завершен'
