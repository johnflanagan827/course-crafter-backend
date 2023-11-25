import os
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import pymysql as MySQLdb
import bcrypt

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'

jwt = JWTManager(app)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)


def get_db_connection():
    return MySQLdb.connect(host='course-crafter.cbzvp1yumkcc.us-east-2.rds.amazonaws.com', user='jflanag5', passwd='goirish!', db='course_crafter')


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

    if len(password) < 8:
        return jsonify({"msg": "Password must be at least 8 characters"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()
        response = make_response(jsonify({"message": "Data inserted successfully", "username": username, "password": password}))
        response.set_cookie('username', 'test')
        return response
    except:
        return jsonify({"msg": "User already exists"}), 400


@app.route('/api/updateAccount', methods=['PUT'])
@jwt_required()
def update_account():
    data = request.json
    new_password = data['password']
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    username = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password_hash = (%s) WHERE username = (%s)", (hashed_password, username,))
        conn.commit()
        cursor.close()
        conn.close()
        response = jsonify({"msg": "Account updated successfully!"}), 200
        return response
    except:
        return jsonify({"msg": "An error occurred"}), 400


@app.route('/api/deleteAccount', methods=['DELETE'])
@jwt_required()
def delete_account():
    username = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE username = (%s)", (username,))
        conn.commit()
        cursor.close()
        conn.close()
        response = jsonify({"msg": "Account deleted successfully!"}), 200
        return response
    except:
        return jsonify({"msg": "An error occurred"}), 400


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
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return jsonify({"msg": "Invalid password"}), 400
    else:
        return jsonify({"msg": "User not found"}), 404

    cursor.close()
    conn.close()

    return jsonify({"msg": "Login success", "access_token": access_token}), 200


@app.route('/api/search', methods=['GET'])
def search():
    search = request.headers.get('search')
    capitalized_search = ' '.join(word.capitalize() for word in search.split())

    search_pattern = "%" + capitalized_search + "%"

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT course_name FROM course WHERE course_name like (%s)", (search_pattern,))
        result = cursor.fetchall()
        if result:
            cursor.close()
            conn.close()
            return jsonify(result), 200
        else:
            return jsonify({"msg": "Classes not found"}), 404
    except:
        return jsonify({"msg": "Classes not found"}), 404


@app.route('/api/csClasses', methods=['GET'])
def cs_classes():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM ComputerScienceClasses")
        courses = cursor.fetchall()

        course_dict = {"AP/Summer": {"name": "AP/Summer", "items": []}}
        for course in courses:
            class_id, class_name, credits, semester, is_fixed, attribute = course

            if semester not in course_dict:
                course_dict[semester] = {
                    "name": semester,
                    "items": []
                }

            course_dict[semester]["items"].append({
                "id": str(class_id),
                "content": class_name,
                "credits": int(credits),
                "isFixed": bool(is_fixed),
                "attribute": attribute
            })

        if course_dict:
            return jsonify(course_dict), 200
        else:
            return jsonify({"msg": "No courses found"}), 404
    except Exception as e:
        return jsonify({"msg": str(e)}), 500
    finally:
        cursor.close()


def find_entry_with_least_credits(task_status):
    min_credits = float('inf')
    semester_with_min_credits = None

    for semester, data in task_status.items():
        total_credits = sum(item['credits'] for item in data['items'])
        if total_credits < min_credits:
            min_credits = total_credits
            semester_with_min_credits = semester

    return semester_with_min_credits


@app.route('/api/getConcentrations', methods=['GET'])
def get_concentrations():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT ConcentrationID, ConcentrationName FROM Concentrations")
        concentrations = cursor.fetchall()
        concentration_list = [{'id': cid, 'name': name} for cid, name in concentrations]
        return jsonify(concentration_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/updateConcentration', methods=['POST'])
def update_concentration():
    data = request.get_json()
    task_status = data.get('taskStatus')
    concentration_id = data.get('concentrationId')

    if not task_status or concentration_id is None:
        return jsonify({'error': 'Missing taskStatus or concentrationId'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Retrieve original CS curriculum classes
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed FROM ComputerScienceClasses")
        cs_classes = cursor.fetchall()
        cs_class_dict = {str(class_id): {"content": class_name, "credits": credits, "isFixed": bool(is_fixed)} for class_id, class_name, credits, _, is_fixed in cs_classes}

        # Update task_status with original CS curriculum
        for semester_data in task_status.values():
            for item in semester_data['items']:
                if item['id'] in cs_class_dict:
                    item.update(cs_class_dict[item['id']])

        # Handle the selected concentration
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed FROM ConcentrationClasses WHERE ConcentrationID = %s", (concentration_id,))
        concentration_classes = cursor.fetchall()

        if concentration_classes:
            for class_id, class_name, credits, semester, is_fixed in concentration_classes:
                found = False
                for semester_name, semester_data in task_status.items():
                    for item in semester_data['items']:
                        if item['id'] == str(class_id):
                            item.update({'content': class_name, 'credits': credits, 'isFixed': bool(is_fixed)})
                            found = True
                            break
                    if found:
                        break

                if not found:
                    semester_with_least_credits = find_entry_with_least_credits(task_status)
                    task_status[semester_with_least_credits]['items'].append({
                        'id': str(class_id),
                        'content': class_name,
                        'credits': credits,
                        'isFixed': bool(is_fixed)
                    })

        return jsonify(task_status), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/getMinors', methods=['GET'])
def get_minors():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT minorID, minorName FROM Minors")
        minors = cursor.fetchall()
        minor_list = [{'id': mid, 'name': name} for mid, name in minors]
        return jsonify(minor_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/updateMinors', methods=['POST'])
def update_minors():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        task_status = request.json.get('taskStatus')
        minor_id = request.json.get('minorId')  # ID of the minor

        # Remove entries with ID outside the range of 1-41
        for semester in task_status.values():
            semester['items'] = [item for item in semester['items'] if 1 <= int(item['id']) <= 41]

        # Remove entries with ID 26 and 36 if their name is "Technical Elective"
        for semester in task_status.values():
            semester['items'] = [item for item in semester['items'] if not (item['id'] in ['26', '36'] and item['content'] == "Technical Elective")]

        # Fetch classes associated with the minor
        cursor.execute("SELECT classID, className, credits, isFixed FROM MinorClasses WHERE minorID = %s", (minor_id,))
        minor_classes = cursor.fetchall()

        # Update the task status with classes from the selected minor
        for class_id, class_name, credits, is_fixed in minor_classes:
            # Check if the class with ID 26 or 36 already exists and is not "Technical Elective"
            existing_classes = [item for semester in task_status.values() for item in semester['items']]
            if str(class_id) in ['26', '36'] and any(item['id'] == str(class_id) and item['content'] != "Technical Elective" for item in existing_classes):
                continue  # Skip adding this class

            semester_with_least_credits = find_entry_with_least_credits(task_status)
            task_status[semester_with_least_credits]['items'].append({
                'id': str(class_id),
                'content': class_name,
                'credits': credits,
                'isFixed': bool(is_fixed)
            })

        # Return the updated task status
        return jsonify(task_status), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
