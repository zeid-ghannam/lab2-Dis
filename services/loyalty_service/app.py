from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from schemas import LoyaltyInfoResponseSchema

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')

db = SQLAlchemy(app)

class Loyalty(db.Model):
    __tablename__ = 'loyalty'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    reservation_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(80), nullable=False, default='BRONZE')
    discount = db.Column(db.Integer, nullable=False, default=5)

@app.route('/manage/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route('/loyalty', methods=['GET'])
def get_loyalty():
    username = request.headers.get('X-User-Name')
    loyalty = Loyalty.query.filter_by(username=username).first()
    
    if not loyalty:
        loyalty = Loyalty(username=username)
        db.session.add(loyalty)
        db.session.commit()
    loyalty_info_schema = LoyaltyInfoResponseSchema()
    loyalty_info_data = {
        "status": loyalty.status,
        "discount": loyalty.discount,
        "reservationCount": loyalty.reservation_count
    }
    loyalty_info_response = loyalty_info_schema.load(loyalty_info_data)
    return jsonify(loyalty_info_response), 200

@app.route('/loyalty', methods=['POST'])
def update_loyalty():
    username = request.headers.get('X-User-Name')
    loyalty = Loyalty.query.filter_by(username=username).first()
    
    if not loyalty:
        loyalty = Loyalty(username=username)
        db.session.add(loyalty)
    
    loyalty.reservation_count += 1
    
    if loyalty.reservation_count >= 20:
        loyalty.status = 'GOLD'
        loyalty.discount = 10
    elif loyalty.reservation_count >= 10:
        loyalty.status = 'SILVER'
        loyalty.discount = 7
    
    db.session.commit()
    
    return jsonify({
        # "username": loyalty.username,
        "status": loyalty.status,
        "discount": loyalty.discount,
        "reservationCount": loyalty.reservation_count
    }), 200

@app.route('/loyalty/decrease', methods=['POST'])
def decrease_loyalty():
    username = request.headers.get('X-User-Name')
    loyalty = Loyalty.query.filter_by(username=username).first()
    
    if not loyalty:
        return jsonify({"message": "Loyalty record not found"}), 404
    
    loyalty.reservation_count = max(0, loyalty.reservation_count - 1)
    
    if loyalty.reservation_count < 10:
        loyalty.status = 'BRONZE'
        loyalty.discount = 5
    elif loyalty.reservation_count < 20:
        loyalty.status = 'SILVER'
        loyalty.discount = 7
    
    db.session.commit()
    
    return jsonify({
        "status": loyalty.status,
        "discount": loyalty.discount,
        "reservationCount": loyalty.reservation_count
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        loyalties = [{
            "username": "Test Max",
            "reservation_count": 25,
            "status": "GOLD",
            "discount": 10,
        }]
        for l in loyalties:
            loyalty = Loyalty(**l)
            db.session.add(loyalty)
        
        db.session.commit()

    app.run(host='0.0.0.0', port=8050)