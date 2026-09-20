import logging

from rest_framework.exceptions import ValidationError

from api.constants import MsgConstants as MSG
from product.constants import Status
from product.models import Order
from user.models import VarificationCode

logger = logging.getLogger(__name__)


class AuthValidator:
    """Валидаторы для аутентификации пользователя."""

    @staticmethod
    def check_is_verified(user, email: str) -> None:
        """
        Если пользователь уже зарегистрирован,
        то ему не нужно подтверждать почту.
        """
        if user.is_active is True:
            raise ValidationError(
                MSG.EMAIL_ALREADY_CONFIRMED.format(email=email)
            )

    @staticmethod
    def check_confirmation_code(user, code: str) -> None:
        """
        Проверяет код подтверждения.
        Если проверка пройдена, то код удаляется.
        """
        try:
            verification_code = VarificationCode.objects.get(
                user=user, code=code,
            )
        except VarificationCode.DoesNotExist:
            raise ValidationError('Введен неверный код.')

        verification_code.delete()


class ProfileValidator:
    """Валидаторы для профиля пользователя."""

    @staticmethod
    def can_user_delete_himself(user) -> None:
        """
        Администратору запрещено удалять себя.

        Нельзя удалить свой профиль при наличии активных заказов.
        """
        if user.is_superuser:
            logger.warning(
                'Администратор с id %s попытался '
                'изменить свой объект пользователя',
                user.id,
            )
            raise ValidationError(
                'Администратор не может удалить свой профиль.'
            )

        elif Order.objects.filter(status=Status.PENDING, user=user).exists():
            raise ValidationError(
                'Нельзя удалить профиль, пока существуют активные заказы.'
            )
