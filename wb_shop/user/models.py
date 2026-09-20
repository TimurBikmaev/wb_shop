from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import (
    MinLengthValidator,
    MinValueValidator,
    RegexValidator
)
from django.db import models

from core.constants import MoneyConstants
from core.mixins import CreatedUpdatedMixin, PublicIdMixin
from user.constants import AuthConstants, UserConstants


class CustomUserManager(BaseUserManager):
    """
    Менеджер для создания пользователя.

    Обязательные поля при создании любого пользователя:
    почта, имя и пароль.
    """

    def create_user(self, email, password, **extra_fields) -> AbstractUser:
        """Создает и сохраняет любого пользователя."""
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
            self,
            email,
            password,
            **extra_fields,
    ) -> AbstractUser:
        """
        Создает и сохраняет администратора.

        Администратору также необходимо создать
        свою корзину через django shell.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class User(PublicIdMixin, CreatedUpdatedMixin, AbstractUser):
    """
    Представляет пользователя в интернет-магазине.

    Хранит информацию об email, имени, балансе
    и дате добавления и обновления профиля.
    """
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']

    username = None
    email = models.EmailField('Email', unique=True)
    first_name = models.CharField(
        'Имя',
        max_length=UserConstants.NAME_MAX_LENGTH,
        validators=[
            MinLengthValidator(UserConstants.NAME_MIN_LENGTH),
        ],
    )
    balance = models.DecimalField(
        'Баланс',
        max_digits=MoneyConstants.MAX_DIGITS,
        decimal_places=MoneyConstants.DECIMAL_PLACES,
        default=MoneyConstants.NO_MONEY,
        validators=[MinValueValidator(MoneyConstants.NO_MONEY)],
    )

    objects = CustomUserManager()

    class Meta:
        db_table = 'user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self) -> str:
        return f'{self.first_name} | {self.email}'

    def __repr__(self) -> str:
        return f'<User(id={self.id}, email={self.email})>'


class VarificationCode(models.Model):
    """Хранит код для подтверждения email пользователя."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(
        'Код потверждения',
        max_length=AuthConstants.EMAIL_CODE_MAX_LENGTH,
        validators=[RegexValidator(AuthConstants.EMAIL_CODE_REGEX)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_verification_code'
