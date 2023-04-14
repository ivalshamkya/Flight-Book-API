from datetime import *
import mysql.connector
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import secrets

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'super-secret'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=2)
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


def jwt_authenticate(username, password):
  user = next((user for user in get_users() if user.username == username), None)
  print(user.username for user in get_users())
  if user and secrets.compare_digest(user.password.encode('utf-8'), password.encode('utf-8')):
    return user

def get_users():
  cursor = db.cursor()
  cursor.execute('SELECT * FROM users')
  rows = cursor.fetchall()
  users = []
  for row in rows:
    users.append(User(row[0], row[2], row[4]))
  return users

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

@app.route('/users', methods=['GET'])
@jwt_required()
def list_users():
  users = get_users()
  return jsonify([user.__dict__ for user in users]), 200

@app.route('/users', methods=['POST'])
@jwt_required()
def add_user():
  name = request.json['name']
  email = request.json['email']
  cursor = db.cursor()
  cursor.execute('INSERT INTO users (name, email) VALUES (%s, %s)', (name, email))
  db.commit()
  return jsonify({'message': 'User added successfully'}), 200

@app.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
  name = request.json['name']
  email = request.json['email']
  cursor = db.cursor()
  cursor.execute('UPDATE users SET name=%s, email=%s WHERE id=%s', (name, email, user_id))
  db.commit()
  return jsonify({'message': 'User updated successfully'}), 200

@app.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
  cursor = db.cursor()
  cursor.execute('DELETE FROM users WHERE id=%s', (user_id,))
  db.commit()
  return jsonify({'message': 'User deleted successfully'}), 200

if __name__ == '__main__':
  app.run(debug=True)
