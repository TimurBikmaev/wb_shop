from typing import List

from django.contrib.auth.models import AbstractUser
from django.db import models

from core.constants import BalanceConstants
from core.mixins import CreatedUpdatedMixin, PublicIdMixin
from user.constants import UserConstants


class User(PublicIdMixin, CreatedUpdatedMixin, AbstractUser):
    """Модель пользователя"""
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: List = []

    email = models.EmailField('Email', unique=True)
    first_name = models.CharField(
        'Имя',
        max_length=UserConstants.NAME_MAX_LENGTH,
    )
    balance = models.DecimalField(
        'Баланс',
        max_digits=BalanceConstants.MAX_DIGITS,
        decimal_places=BalanceConstants.DECIMAL_PLACES,
        default=BalanceConstants.NO_MONEY,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.first_name} | {self.email}'

    def __repr__(self):
        return f'<User(id={self.id}, email={self.email})>'
