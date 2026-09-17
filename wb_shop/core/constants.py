from decimal import Decimal


class MoneyConstants:
    DECIMAL_PLACES = 2
    MAX_DIGITS = 8
    NO_MONEY = Decimal('0.00')
    PRICE_MIN_VALUE = Decimal('1.00')
    TOTAL_PRICE_MIN_VALUE = Decimal('1.00')


class LoggingConstants:
    BACKUP_COUNT = 5
    CONFIG_VERSION = 1
    FILE_MAX_SIZE = 10 * 1024 * 1024


class PublicIdConstants:
    MAX_LENGTH = 8
    URL_REGEX = rf'[a-zA-Z0-9]{{{MAX_LENGTH}}}'


class TokenConstants:
    EXPIRE_ACCESS_MINUTS = 30
    EXPIRE_REFRESH_DAYS = 7
