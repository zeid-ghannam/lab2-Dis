from marshmallow import Schema, fields, validate, EXCLUDE
from enum import Enum

class LoyaltyStatus(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"

class LoyaltyInfoResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    status = fields.Str(validate=validate.OneOf([s.value for s in LoyaltyStatus]))
    discount = fields.Integer()
    reservationCount = fields.Integer()