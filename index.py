from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import pymysql as MySQLdb

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'

jwt = JWTManager(app)
CORS(app, supports_credentials=True)


def get_db_connection():
    return MySQLdb.connect(host='127.0.0.1', user='jflanag5', passwd='g6Mz_jj8}]A.]{e-', db='course_crafter')


@app.route('/api/update', methods=['POST'])
def update_data():
    data = request.json
    name = data['name']
    age = data['age']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO age (name, age) VALUES (%s, %s)", (name, age))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Data inserted successfully"})


@app.route('/api/createAccount', methods=['POST'])
def create_account():
    data = request.json
    username = data['username']
    password = data['password']

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password))
        conn.commit()
        cursor.close()
        conn.close()
        response = make_response(jsonify({"message": "Data inserted successfully", "username": username, "password": password}))
        response.set_cookie('username', 'test')
        return response
    except:
        return jsonify({"msg": "User already exists"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)
    access_token = create_access_token(identity=username)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = (%s)", (username,))
    result = cursor.fetchone()

    if result:
        password_hash = result[0]
        if password_hash != password:
            return jsonify({"msg": "invalid password"}), 400
    else:
        return jsonify({"msg": "User not found"}), 400

    cursor.close()
    conn.close()

    return jsonify({"msg": "Login success", "access_token": access_token}), 200


@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    return jsonify({"msg": f"You have access to this endpoint! {get_jwt_identity()}"})


if __name__ == '__main__':
    app.run(debug=True, port=5328)
