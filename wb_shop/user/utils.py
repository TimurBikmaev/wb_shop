import secrets

from user.constants import AuthConstants


def generate_code() -> str:
    """Генерация 4-х значного кода для подтверждения email."""
    return f'{secrets.randbelow(AuthConstants.EMAIL_CODE_RANDOM_NUMBER):04d}'
