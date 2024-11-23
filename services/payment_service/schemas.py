from marshmallow import Schema, fields, validate, EXCLUDE
from enum import Enum

class PaymentStatus(str, Enum):
    PAID = "PAID"
    REVERSED = "REVERSED"
    CANCELED = "CANCELED"

class PaymentInfoSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    paymentUid = fields.UUID()
    status = fields.Str(validate=validate.OneOf([s.value for s in PaymentStatus]))
    price = fields.Integer()

class PaymentDetailsSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    paymentUid = fields.UUID()
    reservationUid = fields.UUID(required=True)
    status = fields.Str(validate=validate.OneOf([s.value for s in PaymentStatus]))
    price = fields.Integer()

class CreatePaymentRequestSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    status = fields.Str(validate=validate.OneOf([s.value for s in PaymentStatus]))
    price = fields.Integer(required=True)
    reservationUid = fields.UUID(required=True)