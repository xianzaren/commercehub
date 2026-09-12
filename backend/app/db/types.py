from sqlalchemy.dialects.mysql import BIGINT, DATETIME, DECIMAL

BIGINT_UNSIGNED = BIGINT(unsigned=True)
MONEY = DECIMAL(12, 2)
UTC_DATETIME = DATETIME(fsp=6)
