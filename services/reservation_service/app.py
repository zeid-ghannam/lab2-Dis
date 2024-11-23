from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload

from schemas import CreateReservationRequestSchema, CreateReservationResponseSchema, ReservationResponseSchema

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
db = SQLAlchemy(app)

class Hotel(db.Model):
    __tablename__ = 'hotels'
    id = db.Column(db.Integer, primary_key=True)
    hotelUid = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    country = db.Column(db.String(80), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    stars = db.Column(db.Integer)
    price = db.Column(db.Integer, nullable=False)
    reservations = db.relationship("Reservation", back_populates="hotel_relation")

class Reservation(db.Model):
    __tablename__ = 'reservation'
    id = db.Column(db.Integer, primary_key=True)
    reservationUid = db.Column(db.String(36), unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    paymentUid = db.Column(db.String(36), nullable=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'))
    status = db.Column(db.String(20), nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    hotel_relation = db.relationship('Hotel', foreign_keys=[hotel_id], back_populates="reservations")

@app.route('/manage/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route('/hotels', methods=['GET'])
def get_hotels():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    hotels = Hotel.query.paginate(page=page, per_page=size)

    response = {
        "page": page,
        "pageSize": size,
        "totalElements": hotels.total,
        "items": [hotel_to_dict(h) for h in hotels.items]
    }

    return jsonify(response), 200

@app.route('/hotels/<string:hotel_uid>', methods=['GET'])
def get_hotel(hotel_uid):
    hotel = Hotel.query.filter_by(hotel_uid=hotel_uid).first()
    if not hotel:
        return jsonify({"message": "Hotel not found"}), 404
    
    return jsonify(hotel_to_dict(hotel)), 200

@app.route('/reservations', methods=['GET', 'POST'])
def reservations():
    username = request.headers.get('X-User-Name')
    if request.method == 'GET':
        reservations_response_schema = ReservationResponseSchema(many=True)
        user_reservations = Reservation.query.filter_by(username=username)\
            .options(joinedload(Reservation.hotel_relation))\
            .all()
        reservation_data = []
        for reservation in user_reservations:
            hotel = Hotel.query.get(reservation.hotel_id)
            if not hotel:
                continue
            reservation_dict = {
                "reservationUid": reservation.reservationUid,
                "hotel": hotel.__dict__,
                "startDate": reservation.start_date.strftime("%Y-%m-%d"),
                "endDate": reservation.end_date.strftime("%Y-%m-%d"),
                # "status": reservation.status,
                # "payment_uid": reservation.paymentUid
            }
            reservation_data.append(reservation_dict)
       
        user_reservations_response = reservations_response_schema.load(reservation_data)
        # print(user_reservations_response, file=sys.stderr)
        return jsonify(user_reservations_response), 200
    else:  # POST

        data = request.json
        hotel = Hotel.query.filter_by(hotelUid=data['hotelUid']).first()
        if not hotel:
            return jsonify({"message": "Hotel not found"}), 404
        
        create_reservation_request_schema = CreateReservationRequestSchema()

        reservation_data = create_reservation_request_schema.dump({
            "hotel_id":hotel.id,
            "start_date":data['startDate'],
            "end_date":data['endDate']
        })
        new_reservation = Reservation(
            reservationUid=str(uuid.uuid4()),
            username=username,
            hotel_id=hotel.id,
            start_date=datetime.strptime(data['startDate'], "%Y-%m-%d") ,
            end_date=datetime.strptime(data['endDate'], "%Y-%m-%d")
        )
        db.session.add(new_reservation)
        db.session.commit()

        create_reservation_response_schema = CreateReservationResponseSchema()
        response = {
            "reservationUid": new_reservation.reservationUid,
            "hotelUid": hotel.hotelUid,
            "price": hotel.price,
            "startDate": new_reservation.start_date.strftime("%Y-%m-%d"),
            "endDate": new_reservation.end_date.strftime("%Y-%m-%d")
        }
        new_reservations_response = create_reservation_response_schema.load(response)
        return jsonify(new_reservations_response), 200

@app.route('/reservations/<string:reservation_uid>', methods=['GET', 'DELETE'])
def reservation(reservation_uid):
    username = request.headers.get('X-User-Name')
    reservation = Reservation.query.filter_by(reservationUid=reservation_uid, username=username)\
                                    .options(joinedload(Reservation.hotel_relation))\
                                    .first()
    if not reservation:
        return jsonify({"message": "Reservation not found"}), 404

    if request.method == 'GET':
        reservations_response_schema = ReservationResponseSchema()
        hotel = Hotel.query.get(reservation.hotel_id)
        if not hotel:
            return jsonify({"message": "Hotel related to this reservation not found"}), 404
        reservation_dict = {
            "reservationUid": reservation.reservationUid,
            "hotel": hotel.__dict__,
            "startDate": reservation.start_date.strftime("%Y-%m-%d"),
            "endDate": reservation.end_date.strftime("%Y-%m-%d")
        }
        user_reservations_response = reservations_response_schema.load(reservation_dict)
        
        return jsonify(user_reservations_response), 200
    else:  # DELETE
        reservation.status = "CANCELED"
        db.session.commit()
        return jsonify({"message": "Бронь успешно отменена"}), 204


@app.route('/reservations/<string:reservation_uid>', methods=['PATCH'])
def update_reservation(reservation_uid):
    data = request.json
    reservation = Reservation.query.filter_by(reservation_uid=reservation_uid).first_or_404()
    if 'paymentUid' in data:
        reservation.payment_uid = data['paymentUid']
        reservation.status = "PAID"
    db.session.commit()
    return jsonify({
        "reservationUid": reservation_uid,
        "paymentUid": reservation.payment_uid
    }), 204

def hotel_to_dict(hotel):
    return {
        "hotelUid": hotel.hotelUid,
        "name": hotel.name,
        "country": hotel.country,
        "city": hotel.city,
        "address": hotel.address,
        "stars": hotel.stars,
        "price": hotel.price
    }

def reservation_to_dict(reservation):
    hotel = Hotel.query.get(reservation.hotel_id)
    return {
        "reservationUid": reservation.reservationUid,
        "hotel": hotel.name,
        "hotelUid": hotel.hotel_uid,
        "status": reservation.status,
        "startDate": reservation.start_date.isoformat(),
        "endDate": reservation.end_date.isoformat()
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        hotels_data = [
            {
                'hotelUid': "049161bb-badd-4fa8-9d90-87c9a82b0668",
                'name': 'Ararat Park Hyatt Moscow',
                'country': 'Россия',
                'city': 'Москва',
                'address': 'Неглинная ул., 4',
                'stars': 5,
                'price': 10000
            },
            {
                'hotelUid': str(uuid.uuid4()),
                'name': 'Seaside Resort',
                'country': 'Spain',
                'city': 'Barcelona',
                'address': '45 Beach Road',
                'stars': 4,
                'price': 200
            },
            {
                'hotelUid': str(uuid.uuid4()),
                'name': 'Mountain View Lodge',
                'country': 'Switzerland',
                'city': 'Zurich',
                'address': '78 Alpine Way',
                'stars': 4,
                'price': 250
            }
        ]

        # Insert hotels
        for hotel_data in hotels_data:
            hotel = Hotel(**hotel_data)
            db.session.add(hotel)
        
        db.session.commit()

        first_hotel = Hotel.query.first()
        
        reservations_data = [
            {
                'reservationUid': "e3005d7d-05ad-4cb2-b144-1be47df80794",
                'username': 'Test Max',
                'paymentUid': str(uuid.uuid4()),
                'hotel_id': first_hotel.id,
                'status': 'PAID',
                'start_date': datetime.now().date(),
                'end_date': (datetime.now() + timedelta(days=3)).date()
                # 'start_date': "2021-10-08",
                # 'end_date': "2021-10-11"
            },
            # {
            #     'reservationUid': str(uuid.uuid4()),
            #     'username': 'Test Max',
            #     'paymentUid': str(uuid.uuid4()),
            #     'hotel_id': first_hotel.id,
            #     'status': 'RESERVED',
            #     'start_date': datetime.now(),
            #     'end_date': datetime.now() + timedelta(days=3)
            # },
            # {
            #     'reservationUid': str(uuid.uuid4()),
            #     'username': 'Test Max',
            #     'paymentUid': str(uuid.uuid4()),
            #     'hotel_id': first_hotel.id,
            #     'status': 'RESERVED',
            #     'start_date': datetime.now() + timedelta(days=5),
            #     'end_date': datetime.now() + timedelta(days=8)
            # }
        ]

        # Insert reservations
        for reservation_data in reservations_data:
            reservation = Reservation(**reservation_data)
            db.session.add(reservation)
        
        db.session.commit()
    app.run(host='0.0.0.0', port=8070)
