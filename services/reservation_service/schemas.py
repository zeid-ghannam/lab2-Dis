from typing import Any, Dict
from marshmallow import Schema, fields, post_load, validate, EXCLUDE
from enum import Enum

class HotelResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    hotelUid = fields.UUID(data_key="hotelUid")
    name = fields.Str()
    country = fields.Str()
    city = fields.Str()
    address = fields.Str()
    stars = fields.Integer(validate=validate.Range(min=1, max=5))
    price = fields.Integer()

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

class PaginationResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    page = fields.Integer()
    pageSize = fields.Integer()
    totalElements = fields.Integer()
    items = fields.List(fields.Nested(HotelResponseSchema))


class ReservationStatus(str, Enum):
    PAID = "PAID"
    RESERVED = "RESERVED"
    CANCELED = "CANCELED"

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

class CreateReservationRequestSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    hotelUid = fields.UUID(required=True)
    startDate = fields.Date(format="%Y-%m-%d", required=True)
    endDate = fields.Date(format="%Y-%m-%d", required=True)

class CreateReservationResponseSchema(Schema):
    class Meta:
        unknown = EXCLUDE
    
    reservationUid = fields.UUID(required=True)
    hotelUid = fields.UUID(required=True)
    price = fields.Integer()
    startDate = fields.Date(format="%Y-%m-%d", required=True)
    endDate = fields.Date(format="%Y-%m-%d", required=True)

    @post_load
    def change_dates_to_str(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        
        data['startDate'] = data['startDate'].strftime("%Y-%m-%d")
        data['endDate'] = data['endDate'].strftime("%Y-%m-%d")
            
        return data