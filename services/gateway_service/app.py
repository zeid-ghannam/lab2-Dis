from functools import wraps
from http import HTTPStatus
import logging
from flask import Flask, request, jsonify
from marshmallow import ValidationError
import requests
import os
from datetime import datetime
from schemas import (
    ReservationResponseSchema,
    HotelPaginationSchema,
    LoyaltySchema,
    HotelResponseSchema,
    PaymentSchema,
    ReservationSchema,
    ErrorSchema,
    ValidationErrorSchema
    )


app = Flask(__name__)

RESERVATION_SERVICE_URL = os.environ.get('RESERVATION_SERVICE_URL', 'http://localhost:8070')
PAYMENT_SERVICE_URL = os.environ.get('PAYMENT_SERVICE_URL', 'http://localhost:8060')
LOYALTY_SERVICE_URL = os.environ.get('LOYALTY_SERVICE_URL', 'http://localhost:8050')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors

def validate_request_schema(schema_cls):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            schema = schema_cls()
            try:
                if request.is_json:
                    data = schema.load(request.json)
                    request.validated_data = data
                return f(*args, **kwargs)
            except ValidationError as err:
                raise SchemaValidationError("Validation error", err.messages)
        return wrapper
    return decorator


def handle_service_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SchemaValidationError as e:
            error_schema = ValidationErrorSchema()
            return jsonify(error_schema.dump({
                "message": str(e),
                "errors": e.errors
            })), HTTPStatus.BAD_REQUEST
        except requests.exceptions.ConnectionError:
            error_schema = ErrorSchema()
            return jsonify(error_schema.dump({
                "message": "Service temporarily unavailable"
            })), HTTPStatus.SERVICE_UNAVAILABLE
        except requests.exceptions.RequestException as e:
            error_schema = ErrorSchema()
            return jsonify(error_schema.dump({
                "message": "Internal service error"
            })), HTTPStatus.INTERNAL_SERVER_ERROR
    return wrapper


class ServiceClient:
    def __init__(self):
        self.hotel_schema = HotelResponseSchema()
        self.payment_schema = PaymentSchema()
        self.loyalty_schema = LoyaltySchema()
        self.reservation_schema = ReservationSchema()
        self.hotel_pagination_schema = HotelPaginationSchema()
    
    @staticmethod
    def _check_user_header(headers):
        if 'X-User-Name' not in headers:
            raise SchemaValidationError("X-User-Name header is required")
        return headers.get('X-User-Name')

    def make_request(self, method, url, schema=None, **kwargs):
        """Make HTTP request with schema validation"""
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            
            if schema and response.content:
                try:
                    return schema.load(response.json())
                except ValidationError as e:
                    logger.info(response.json())
                    logger.error(f"Schema validation error for {url}: {e.messages}")
                    raise SchemaValidationError("Invalid response format", e.messages)
            
            return response.json() if response.content else None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}")
            if response.status_code == HTTPStatus.NOT_FOUND:
                raise SchemaValidationError("Resource not found")
            raise

    def get_hotel(self, hotel_uid):
        """Get hotel details with schema validation"""
        return self.make_request(
            'GET', 
            f"{RESERVATION_SERVICE_URL}/hotels/{hotel_uid}",
            schema=self.hotel_schema
        )

    def get_hotels(self, page, size):
        """Get paginated hotels with schema validation"""
        return self.make_request(
            'GET',
            f"{RESERVATION_SERVICE_URL}/hotels",
            params={"page": page, "size": size},
            schema=self.hotel_pagination_schema
        )

    def get_user_reservations(self, username):
        reservations = self.make_request(
            'GET',
            f"{RESERVATION_SERVICE_URL}/reservations",
            headers={"X-User-Name": username},
            schema=ReservationResponseSchema(many=True)
        )
        if reservations:
            all_user_reservations = []
            for reservation in reservations:
                payment = self.make_request(
                    'GET',
                    f"{PAYMENT_SERVICE_URL}/payment/{reservation['reservationUid']}",
                    headers={"X-User-Name": username},
                )
                if not payment:
                    reservation["payment"] = {}
                    reservation["status"] = "RESERVED"
                else:
                    del payment["paymentUid"]
                    reservation["payment"] = payment
                    reservation["status"] = payment["status"]
                all_user_reservations.append(reservation)
            return all_user_reservations

    def get_reservation_by_id(self, username, reservation_uid):
        reservation = self.make_request(
            'GET',
            f"{RESERVATION_SERVICE_URL}/reservations/{reservation_uid}",
            headers={"X-User-Name": username},
            schema=ReservationResponseSchema()
        )
        if reservation:
            payment = self.make_request(
                'GET',
                f"{PAYMENT_SERVICE_URL}/payment/{reservation['reservationUid']}",
                headers={"X-User-Name": username},
            )
            if not payment:
                reservation["payment"] = {}
                reservation["status"] = "RESERVED"
            else:
                del payment["paymentUid"]
                reservation["payment"] = payment
                reservation["status"] = payment["status"]
            return reservation

    def delete_reservation_by_id(self, username, reservation_uid):
        reservation = self.make_request(
            'DELETE',
            f"{RESERVATION_SERVICE_URL}/reservations/{reservation_uid}",
            headers={"X-User-Name": username}
        )
        if reservation is None:
            
            payment = self.make_request(
                'GET',
                f"{PAYMENT_SERVICE_URL}/payment/{reservation_uid}",
                headers={"X-User-Name": username},
            )
            if not payment:
                return 501
            else:
                delete_payment = self.make_request(
                    'DELETE',
                    f"{PAYMENT_SERVICE_URL}/payment/{payment['paymentUid']}",
                    headers={"X-User-Name": username},
                )
                if delete_payment is None:
                    return 204
        return 504

    def create_reservation(self, username, request_data):
        """Handle creation of a new reservation across services"""
        reservation = self.make_request(
            'POST',
            f"{RESERVATION_SERVICE_URL}/reservations",
            headers={"X-User-Name": username},
            json=request_data,
        )
        if reservation:
            reservation["status"] = "RESERVED"
            
            #calculate total payment (before discount)
            start_date = datetime.fromisoformat(reservation['startDate'])
            end_date = datetime.fromisoformat(reservation['endDate'])
            nights = (end_date - start_date).days
            total_price = reservation['price'] * nights

            # Get loyalty discount
            loyalty = self.make_request(
                'GET',
                f"{LOYALTY_SERVICE_URL}/loyalty",
                headers={"X-User-Name": username}
            )
            discounted_price = total_price * (1 - loyalty['discount'] / 100)
            reservation["discount"] = loyalty['discount']
            
            # Create the payment
            payment_json = {
                        "price": discounted_price,
                        "reservationUid": reservation["reservationUid"],
                        "status":"PAID"
                    }
            payment = self.make_request(
                'POST',
                f"{PAYMENT_SERVICE_URL}/payment",
                headers={"X-User-Name": username},
                json=payment_json
            )
            # change the status
            if payment:
                reservation["payment"] = payment
                reservation["status"] = payment["status"]

                # update loyalty
                loyalty = self.make_request(
                    'POST',
                    f"{LOYALTY_SERVICE_URL}/loyalty",
                    headers={"X-User-Name": username}
                )
            # clean to the schema
            del reservation["price"]

            return reservation
     

    def get_loyalty(self, username):
        """Get loyalty information with schema validation"""
        return self.make_request(
            'GET',
            f"{LOYALTY_SERVICE_URL}/loyalty",
            headers={"X-User-Name": username},
            schema=self.loyalty_schema
        )

service_client = ServiceClient()

@app.route('/api/v1/hotels', methods=['GET'])
@handle_service_error
def get_hotels():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    
    hotels_data = service_client.get_hotels(page, size)
    return jsonify(hotels_data), HTTPStatus.OK


@app.route('/api/v1/reservations', methods=['GET'])
@handle_service_error
def get_reservations():
    username = ServiceClient._check_user_header(request.headers)
    user_reservations = service_client.get_user_reservations(username)
    return jsonify(user_reservations), HTTPStatus.OK

@app.route('/api/v1/reservations', methods=['POST'])
def create_reservation():
    username = ServiceClient._check_user_header(request.headers)
    data = request.json
    user_reservations = service_client.create_reservation(username, data)
    return jsonify(user_reservations), HTTPStatus.OK


@app.route('/api/v1/reservations/<string:reservation_uid>', methods=['GET'])
def get_reservation(reservation_uid):
    username = ServiceClient._check_user_header(request.headers)
    reservation = service_client.get_reservation_by_id(username, reservation_uid)
    return jsonify(reservation), HTTPStatus.OK


@app.route('/api/v1/reservations/<string:reservation_uid>', methods=['DELETE'])
def cancel_reservation(reservation_uid):
    username = ServiceClient._check_user_header(request.headers)
    reservation = service_client.delete_reservation_by_id(username, reservation_uid)
    # TODO:
    return jsonify({"message": "Reservation canceled"}), 204


@app.route('/api/v1/me', methods=['GET'])
@handle_service_error
def get_user_info():
    
    username = ServiceClient._check_user_header(request.headers)
    user_reservations = service_client.get_user_reservations(username)
    
    loyalty = service_client.get_loyalty(username)
    user_info = {
        "reservations": user_reservations,
        "loyalty": loyalty
    }
    return jsonify(user_info), HTTPStatus.OK


@app.route('/api/v1/loyalty', methods=['GET'])
def get_loyalty():
    username = request.headers.get('X-User-Name')
    response = requests.get(f"{LOYALTY_SERVICE_URL}/loyalty", headers={"X-User-Name": username})
    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)