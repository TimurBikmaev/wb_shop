from decimal import Decimal


class BalanceConstants:
    DECIMAL_PLACES = 2
    MAX_DIGITS = 8
    NO_MONEY = Decimal('0.00')


class PublicIdConstants:
    MAX_LENGTH = 8
    URL_REGEX = rf'[a-zA-Z0-9]{{{MAX_LENGTH}}}'
