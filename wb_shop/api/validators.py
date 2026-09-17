from rest_framework.exceptions import ValidationError

from api.constants import MsgConstants as MSG
from user.models import VarificationCode


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
