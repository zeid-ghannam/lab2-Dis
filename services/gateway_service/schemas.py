from typing import Any, Dict
from marshmallow import Schema, fields, post_load, validate, EXCLUDE
from enum import Enum

class ReservationStatus(str, Enum):
    PAID = "PAID"
    RESERVED = "RESERVED"
    CANCELED = "CANCELED"

class PaymentStatus(str, Enum):
    PAID = "PAID"
    REVERSED = "REVERSED"
    CANCELED = "CANCELED"

class LoyaltyStatus(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class HotelResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    hotelUid = fields.UUID(required=True, data_key="hotelUid")
    name = fields.Str(required=True)
    country = fields.Str(required=True)
    city = fields.Str(required=True)
    address = fields.Str(required=True)
    stars = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    price = fields.Float(required=True)

class HotelInfoSchema(Schema):
    """Schema for condensed hotel information"""
    class Meta:
        unknown = EXCLUDE
        
    hotelUid = fields.UUID(required=True, data_key="hotelUid")
    name = fields.Str(required=True)
    country = fields.Str()
    city = fields.Str()
    address = fields.Str()
    fullAddress = fields.Str()
    stars = fields.Int(required=True, validate=validate.Range(min=1, max=5))

    @post_load
    def create_full_address(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        if all(k in data for k in ['country', 'city', 'address']):
            data['fullAddress'] = f"{data['country']}, {data['city']}, {data['address']}"
            del data['country']
            del data['city']
            del data['address']
        return data

class HotelPaginationSchema(Schema):
    """Schema for paginated hotel responses"""
    class Meta:
        unknown = EXCLUDE
        
    page = fields.Int(required=True)
    pageSize = fields.Int(required=True)
    totalElements = fields.Int(required=True)
    items = fields.List(fields.Nested(HotelResponseSchema), required=True)

class ReservationResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    reservationUid = fields.UUID()
    hotel = fields.Nested(HotelInfoSchema, required=True)
    startDate = fields.Date(format="%Y-%m-%d")
    endDate = fields.Date(format="%Y-%m-%d")

    @post_load
    def change_dates_to_str(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        
        data['startDate'] = data['startDate'].strftime("%Y-%m-%d")
        data['endDate'] = data['endDate'].strftime("%Y-%m-%d")
            
        return data

class CreateReservationResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    reservationUid = fields.UUID(required=True)
    hotelUid = fields.UUID(required=True)
    startDate = fields.Date(format="%Y-%m-%d", required=True)
    endDate = fields.Date(format="%Y-%m-%d", required=True)

    @post_load
    def change_dates_to_str(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        
        data['startDate'] = data['startDate'].strftime("%Y-%m-%d")
        data['endDate'] = data['endDate'].strftime("%Y-%m-%d")
            
        return data
    

class PaymentInfoSchema(Schema):
    class Meta:
        unknown = EXCLUDE

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

class LoyaltySchema(Schema):
    """Schema for loyalty program information"""
    class Meta:
        unknown = EXCLUDE
        
    status = fields.Str(required=True, validate=validate.OneOf(['BRONZE', 'SILVER', 'GOLD']))
    discount = fields.Float(required=True)
    reservationCount = fields.Int(required=True)

class HotelPaginationSchema(Schema):
    """Schema for paginated hotel responses"""
    class Meta:
        unknown = EXCLUDE
        
    page = fields.Int(required=True)
    pageSize = fields.Int(required=True)
    totalElements = fields.Int(required=True)
    items = fields.List(fields.Nested(HotelResponseSchema), required=True)

class LoyaltySchema(Schema):
    """Schema for loyalty program information"""
    class Meta:
        unknown = EXCLUDE
        
    status = fields.Str(required=True, validate=validate.OneOf(['BRONZE', 'SILVER', 'GOLD']))
    discount = fields.Float(required=True)
    reservationCount = fields.Int(required=True)

class PaymentSchema(Schema):
    """Schema for payment responses"""
    class Meta:
        unknown = EXCLUDE
        
    paymentUid = fields.UUID(required=True)
    status = fields.Str(required=True, validate=validate.OneOf(['PAID', 'REVERSED', 'CANCELED']))
    price = fields.Float(required=True)


class ReservationSchema(Schema):
    """Schema for reservation details"""
    class Meta:
        unknown = EXCLUDE
        
    reservationUid = fields.UUID(required=True)
    hotel = fields.Nested(HotelInfoSchema, required=True)
    startDate = fields.Date(required=True, format="%Y-%m-%d")
    endDate = fields.Date(required=True, format="%Y-%m-%d")
    status = fields.Str(required=True, validate=validate.OneOf(['PAID', 'RESERVED', 'CANCELED']))
    payment = fields.Nested(PaymentInfoSchema, required=True)


class ErrorSchema(Schema):
    """Schema for error responses"""
    message = fields.Str(required=True, description="Error message")

class ErrorDescriptionSchema(Schema):
    """Schema for validation error details"""
    field = fields.Str(required=True)
    error = fields.Str(required=True)

class ValidationErrorSchema(Schema):
    """Schema for validation error responses"""
    message = fields.Str(required=True)
    errors = fields.List(fields.Nested(ErrorDescriptionSchema), required=True)