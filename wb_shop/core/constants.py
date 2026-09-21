from decimal import Decimal


class AdminConstants:
    NO_EXTRA = 0


class LoggingConstants:
    BACKUP_COUNT = 5
    CONFIG_VERSION = 1
    FILE_MAX_SIZE = 10 * 1024 * 1024


class MoneyConstants:
    CARD_CVC_LENGTH = 3
    CARD_NUMBER_TEST_LENGTH = 5
    DECIMAL_PLACES = 2
    MAX_DIGITS = 8
    NO_MONEY = Decimal('0.00')
    PRICE_MIN_VALUE = Decimal('1.00')
    TOTAL_PRICE_MIN_VALUE = Decimal('1.00')


class PublicIdConstants:
    MAX_LENGTH = 8
    PUBLIC_ID_REGEX = rf'[a-zA-Z0-9]{{{MAX_LENGTH}}}'


class SettingsConstants:
    PAGINATION_PAGE_NUMBER = 5


class TokenConstants:
    EXPIRE_ACCESS_MINUTS = 5
    EXPIRE_REFRESH_DAYS = 7
