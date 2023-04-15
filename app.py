from datetime import *
import mysql.connector
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import secrets

"""
* Konfigurasi JWT dan database.
* JWT_SECRET_KEY berisi secret key untuk JWT access token.
* JWT_ACCESS_TOKEN_EXPIRES berisi waktu berlakunya JWT access token.
* JSON_SORT_KEYS digunakan untuk menonaktifkan pengurutan key dalam JSON response.
"""
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JSON_SORT_KEYS'] = False
jwt = JWTManager(app)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="restful"
)


class User:
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def __str__(self):
        return f'User(id={self.id}, username={self.username}, password={self.password})'

"""
* Method jwt_authenticate(username, password) digunakan untuk otentikasi user berdasarkan username dan password.
"""
def jwt_authenticate(username, password):
    user = next((user for user in get_users()
                if user.username == username), None)
    print(user.username for user in get_users())
    if user and secrets.compare_digest(user.password.encode('utf-8'), password.encode('utf-8')):
        return user

"""
* Method get_users() mengambil semua user dari tabel users dalam database.
"""
def get_users():
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users')
    rows = cursor.fetchall()
    users = []
    for row in rows:
        users.append(User(row[0], row[2], row[4]))
    return users


"""
* Method get_flight_by_city(city) mengambil data penerbangan berdasarkan kota keberangkatan.
"""
def get_flight_by_city(city):
    cursor = db.cursor()
    cursor.execute(f"""
    SELECT flights.flight_id, flights.airline_name, flights.flight_number,
       departure_airport.airport_name AS departure_airport, departure_airport.city AS departure_city,
       arrival_airport.airport_name AS arrival_airport, arrival_airport.city AS arrival_city,
       flights.departure_time, flights.arrival_time, flights.price
    FROM flights
    JOIN airports AS departure_airport ON flights.departure_airport_id = departure_airport.airport_id
    JOIN airports AS arrival_airport ON flights.arrival_airport_id = arrival_airport.airport_id
    WHERE departure_airport.city = '{city}';
    """)
    rows = cursor.fetchall()
    flights = []
    for row in rows:
        flights.append({
          'flight_id': row[0],
          'airline_name': row[1],
          'flight_number': row[2],
          'departure_airport': row[3],
          'departure_city': row[4],
          'arrival_airport': row[5],
          'arrival_city': row[6],
          'departure_time': row[7],
          'arrival_time': row[8],
          'price': row[9],
        })
    return flights


"""
* Method get_flight_seats_availability(flight_id) mengambil data ketersediaan kursi untuk suatu penerbangan.
"""
def get_flight_seats_availability(flight_id):
    cursor = db.cursor()
    cursor.execute(f"""
    SELECT seat_id, seat_number,
       CASE is_available
           WHEN 0 THEN 'Available'
           WHEN 1 THEN 'Booked'
       END AS availability
    FROM seats
    LEFT JOIN flights ON flights.flight_id = seats.flight_id
    WHERE flights.flight_id = {flight_id};
    """)
    rows = cursor.fetchall()
    seats = []
    for row in rows:
        seats.append({
          'seat_id': row[0],
          'seat_number': row[1],
          'availability_status': row[2],
        })
    return seats


"""
* Method get_booking_details(booking_id) mengambil data detail booking berdasarkan booking id.
"""
def get_booking_details(booking_id):
    cursor = db.cursor()
    cursor.execute(f"""
    SELECT b.booking_id, b.booking_time, b.seat_number, f.airline_name, 
      (SELECT airports.airport_name FROM flights LEFT JOIN airports ON flights.departure_airport_id = airports.airport_id WHERE f.flight_id = flights.flight_id) AS departure_airport, 
      (SELECT airports.airport_name FROM flights LEFT JOIN airports ON flights.arrival_airport_id = airports.airport_id WHERE f.flight_id = flights.flight_id) AS arrival_airport 
    FROM bookings b LEFT JOIN flights f ON f.flight_id = b.flight_id WHERE b.booking_id = {booking_id};
    """)
    row = cursor.fetchone()
    details = {
        'booking_id': row[0],
        'booking_time': row[1],
        'seat_number': row[2],
        'airline_name': row[3],
        'departure_airport': row[4],
        'arrival_airport': row[5],
    }
    return details


"""
* Method get_booking_details_by_fid(flight_id, seat_number) mengambil data detail booking berdasarkan flight id dan seat number.
"""
def get_booking_details_by_fid(flight_id, seat_number):
    cursor = db.cursor()
    cursor.execute(f"""
    SELECT b.user_id, b.booking_id, b.booking_time, b.seat_number, f.airline_name, 
      (SELECT airports.airport_name FROM flights LEFT JOIN airports ON flights.departure_airport_id = airports.airport_id WHERE f.flight_id = flights.flight_id) AS departure_airport, 
      (SELECT airports.airport_name FROM flights LEFT JOIN airports ON flights.arrival_airport_id = airports.airport_id WHERE f.flight_id = flights.flight_id) AS arrival_airport 
    FROM bookings b LEFT JOIN flights f ON f.flight_id = b.flight_id WHERE b.flight_id = {flight_id} AND b.seat_number = '{seat_number}';
    """)
    row = cursor.fetchone()
    details = {
        'user_id': row[0],
        'booking_id': row[1],
        'booking_time': row[2],
        'seat_number': row[3],
        'airline_name': row[4],
        'departure_airport': row[5],
        'arrival_airport': row[6],
    }
    return details


"""
* Method not_found_error(error) digunakan sebagai error handler apabila terjadi error 404.
"""
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'status': 404,
        'message': 'The requested resource was not found.',
        'timestamp': datetime.now()
    }), 404


"""
* Endpoint /auth digunakan untuk mengotentikasi pengguna, menerima request POST dengan parameter username dan password. 
* Jika kredensial yang diberikan valid, endpoint akan mengembalikan token akses JWT untuk digunakan di endpoint lainnya.
"""
@app.route('/auth', methods=['POST'])
def authenticate():
    username = request.json.get('username')
    password = request.json.get('password')
    user = jwt_authenticate(username, password)
    if user:
        access_token = create_access_token(identity=user.id)
        return jsonify({'access_token': access_token}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


"""
* Endpoint /users digunakan untuk mengambil daftar semua user (GET), 
* Menambahkan user baru (POST), 
* Mengupdate informasi user yang ada (PUT), 
* Menghapus user (DELETE). 
* Semua endpoint ini membutuhkan autentikasi dengan token akses.
"""
@app.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    users = get_users()
    timestamp = datetime.now()
    return jsonify({'status': 200, 'timestamp': timestamp, 'data': [user.__dict__ for user in users]}), 200

@app.route('/users', methods=['POST'])
@jwt_required()
def add_user():
    name = request.json['name']
    username = request.json['username']
    email = request.json['email']
    password = request.json['password']
    cursor = db.cursor()
    cursor.execute('INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)',
                   (name, username, email, password))
    db.commit()
    timestamp = datetime.now()
    return jsonify({'status': 200, 'timestamp': timestamp, 'message': 'User added successfully'}), 200

@app.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    name = request.json['name']
    username = request.json['username']
    email = request.json['email']
    password = request.json['password']
    cursor = db.cursor()
    cursor.execute('UPDATE users SET name=%s, username=%s, email=%s, password=%s WHERE id=%s',
                   (name, username, email, password, user_id))
    db.commit()
    timestamp = datetime.now()
    return jsonify({'status': 200, 'timestamp': timestamp, 'message': 'User updated successfully'}), 200

@app.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    cursor = db.cursor()
    cursor.execute('DELETE FROM users WHERE id=%s', (user_id,))
    db.commit()
    timestamp = datetime.now()
    return jsonify({'status': 200, 'timestamp': timestamp, 'message': 'User deleted successfully'}), 200




"""
* Endpoint /flight/<city> digunakan untuk mengambil daftar penerbangan dengan tujuan kota tertentu. 
* Endpoint ini membutuhkan autentikasi dengan token akses.
"""
@app.route('/flight/<string:city>', methods=['GET'])
@jwt_required()
def list_flights(city):
    flights = get_flight_by_city(city)
    timestamp = datetime.now()
    return jsonify({'status': 200, 'timestamp': timestamp, 'flights': flights}), 200

"""
* Endpoint /flight/<flight_id>/seats digunakan untuk mengambil daftar kursi yang tersedia untuk penerbangan dengan id tertentu. 
* Endpoint ini membutuhkan autentikasi dengan token akses.
"""
@app.route('/flight/<int:flight_id>/seats', methods=['GET'])
@jwt_required()
def list_flights_seats(flight_id):
    seats = get_flight_seats_availability(flight_id)
    timestamp = datetime.now()
    return jsonify({'status': 200, 'timestamp': timestamp, 'seats': seats}), 200

"""
* Endpoint /flight/<flight_id>/booking/ digunakan untuk memesan kursi untuk penerbangan dengan id tertentu. 
* Endpoint ini membutuhkan autentikasi dengan token akses dan menerima request POST dengan parameter seat_number yang menentukan nomor kursi yang ingin dipesan.
* Jika kursi tersebut tersedia, booking akan dibuat dan detail booking akan dikembalikan. 
* Jika kursi telah dipesan sebelumnya, dan akan mengembalikan pesan dengan code 409 dan memberikan detail booking apabila, id user pada booking tersebut sama dengan id user.
"""
@app.route('/flight/<int:flight_id>/booking/', methods=['POST'])
@jwt_required()
def booking_flight(flight_id):
    user_id = get_jwt_identity()
    seat_number = request.json['seat_number']
    timestamp = datetime.now()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM bookings WHERE flight_id=%s AND seat_number=%s', (flight_id, seat_number))
    booking = cursor.fetchone()
    if booking is not None:
        booking_details = get_booking_details_by_fid(flight_id, seat_number)
        if(booking_details['user_id'] == get_jwt_identity()):
            return jsonify({'status': 409, 'timestamp': timestamp, 'message': 'Seat already booked', 'booking_details': booking_details}), 409
        else:
            return jsonify({'status': 409, 'timestamp': timestamp, 'message': 'Seat already booked'}), 409

    cursor.execute('INSERT INTO `bookings`(`flight_id`, `user_id`, `booking_time`, `seat_number`) VALUES (%s, %s, %s, %s)',
                   (flight_id, user_id, timestamp, seat_number))
    db.commit()

    booking_details = get_booking_details(cursor.lastrowid)

    cursor.execute('UPDATE `seats` SET is_available = %s WHERE flight_id = %s AND seat_number = %s',
                   ('1', flight_id, seat_number))
    db.commit()
    timestamp = datetime.now()
    return jsonify({'status': 200, 'timestamp': timestamp, 'message': 'Seat booked successfully', 'booking_details': booking_details}), 200

"""
* Endpoint /flight/<flight_id>/<seat_number> digunakan untuk menghapus pemesanan kursi untuk penerbangan dengan id tertentu. 
* Endpoint ini membutuhkan autentikasi dengan token akses. 
* Jika pengguna yang mencoba menghapus pemesanan adalah pengguna yang melakukan pemesanan sebelumnya, pemesanan akan dihapus dan pesan konfirmasi akan dikembalikan. 
* Jika pengguna yang mencoba menghapus pemesanan bukan pengguna yang melakukan pemesanan, pesan error akan dikembalikan.
* Jika kursi yang di tuju tidak valid maka, pesan error akan dikembalikan.
"""
@app.route('/flight/<int:flight_id>/<string:seat_number>', methods=['DELETE'])
@jwt_required()
def delete_booking(flight_id, seat_number):
    timestamp = datetime.now()
    cursor = db.cursor()
    cursor.execute('SELECT seat_id FROM seats WHERE flight_id=%s AND seat_number=%s', (flight_id, seat_number))
    row = cursor.fetchone()
    print(row is not None)
    if row is not None:
      cursor.execute('SELECT user_id FROM bookings WHERE flight_id=%s AND seat_number=%s', (flight_id, seat_number))
      row2 = cursor.fetchone()
      if row2 is not None:
          if(row2[0] == get_jwt_identity()):
              cursor.execute('UPDATE `seats` SET is_available = %s WHERE flight_id = %s AND seat_number = %s', ('0', flight_id, seat_number))
              db.commit()

              cursor.execute('DELETE FROM bookings WHERE flight_id=%s AND seat_number=%s', (flight_id, seat_number))
              db.commit()
              return jsonify({'status': 200, 'timestamp': timestamp, 'message': 'Booking deleted successfully.'}), 200
          else:
              return jsonify({'status': 403, 'timestamp': timestamp, 'message': 'You are not authorized to delete this booking data.'}), 403   
      return jsonify({'status': 404, 'timestamp': timestamp, 'message': 'Booking data does not exist'}), 404
    return jsonify({'status': 404, 'timestamp': timestamp, 'message': 'Seat does not exist'}), 404

if __name__ == '__main__':
    app.run(debug=True)
