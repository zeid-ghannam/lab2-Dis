from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import uuid

from schemas import CreatePaymentRequestSchema, PaymentInfoSchema

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)

class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    paymentUid = db.Column(db.String(36), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    reservationUid = db.Column(db.String(36), nullable=False)

@app.route('/manage/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route('/payment', methods=['POST'])
def create_payment():
    data = request.json
    create_payment_request_schema = CreatePaymentRequestSchema()
    payment_info_schema = PaymentInfoSchema()
    payment_creation_data = create_payment_request_schema.dump({
            "status":data["status"],
            "price":data['price'],
            "reservationUid":data['reservationUid']
        })
    new_payment = Payment(
        paymentUid=str(uuid.uuid4()),
        status=data["status"],
        price=data['price'],
        reservationUid=data['reservationUid']
    )
    db.session.add(new_payment)
    db.session.commit()
    payment_info = {
        "status": new_payment.status,
        "price": new_payment.price
    }
    payment_response = payment_info_schema.load(payment_info)
    return jsonify(payment_response), 201

@app.route('/payment/<string:reservationUid>', methods=['GET'])
def get_payment(reservationUid):
    payment = Payment.query.filter_by(reservationUid=reservationUid).first()
    if not payment:
        return jsonify({"message": "No payment related to this reservation"}), 404
    payment_info_schema = PaymentInfoSchema()
    if request.method == 'GET':
        payment_info = {
            "paymentUid": payment.paymentUid,
            "status": payment.status,
            "price": payment.price
        }
        payment_response = payment_info_schema.load(payment_info)
        return jsonify(payment_response), 200


@app.route('/payment/<string:payment_uid>', methods=['DELETE'])
def cancel_payment(payment_uid):
    payment = Payment.query.filter_by(paymentUid=payment_uid).first()
    if not payment:
        return jsonify({"message": "Payment not found"}), 404

    payment.status = "CANCELED"
    db.session.commit()
    return jsonify({"message": "Payment canceled"}), 204

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        payment_data = {
                "paymentUid": str(uuid.uuid4()),
                "reservationUid": "e3005d7d-05ad-4cb2-b144-1be47df80794",
                "status": "PAID",
                "price": 27000,
            }

        payment = Payment(**payment_data)
        db.session.add(payment)
        
        db.session.commit()
    app.run(host='0.0.0.0', port=8060)
