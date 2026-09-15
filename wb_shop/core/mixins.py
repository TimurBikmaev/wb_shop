from django.db import models

from core.constants import PublicIdConstants
from core.utils import generate_public_id


class CreatedUpdatedMixin(models.Model):
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        abstract = True


class PublicIdMixin:
    public_id = models.CharField(
        'Public ID',
        max_length=PublicIdConstants.MAX_LENGTH,
        unique=True,
        default=generate_public_id,
        editable=False
    )

    class Meta:
        abstract = True
