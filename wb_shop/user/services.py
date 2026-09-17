from django.core.mail import send_mail

from user.models import VarificationCode
from user.utils import generate_code


def send_email_code(user) -> None:
    """Оправляет код подтверждения на почту пользователя."""
    code = generate_code()

    VarificationCode.objects.update_or_create(
        user=user,
        defaults={'code': code},
    )

    send_mail(
        subject='Подтверждение email',
        message=f'Ваш код: {code}',
        from_email=None,
        recipient_list=[user.email],
    )
