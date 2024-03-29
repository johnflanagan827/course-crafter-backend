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
        access_token = create_access_token(identity=username)
        response = jsonify({"msg": "Login success", "access_token": access_token}), 200
        return response
    except:
        return jsonify({"msg": "User already exists"}), 400
    
@app.route('/api/rating', methods=['POST'])
def submit_rating():
    data = request.json
    course = data['course'][0]
    difficulty = data['difficulty']
    hours = data['hours']
    grade = data['grade']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO ratings (course_name, difficulty, hours, grade) VALUES (%s, %s, %s, %s)", (course, difficulty, hours, grade))
        conn.commit()
        cursor.close()
        conn.close()
        response = make_response(jsonify({"message": "Data inserted successfully", "course": course, "difficulty": difficulty, "hours": hours, "grade": grade}))
        return response
    except Exception as e:
        return jsonify({"msg": "Insert Failed"}), 400


@app.route('/api/course_details', methods=['GET'])
def getCourseDetails():
    print('hi')
    data = course = request.args.get('course')
    course = data
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT course_name, subject, description, instructor FROM course WHERE course_name = %s", (course,))
        result = cursor.fetchall()
        if result:
            cursor.close()
            conn.close()
            return jsonify(result), 200
        else:
            return jsonify({"msg": "Classes not found"}), 404
    except:
        return jsonify({"msg": "Classes not found"}), 404


@app.route('/api/updateAccount', methods=['PUT'])
@jwt_required()
def update_account():
    data = request.json
    current_password = data['current_password']
    new_password = data['password']
    username = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch the existing password hash from the database
        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        password_hash = cursor.fetchone()[0]

        # Check if the current password is correct
        if bcrypt.checkpw(current_password.encode('utf-8'), password_hash.encode('utf-8')):
            # Hash the new password
            hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            # Update the password in the database
            cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (hashed_new_password, username))
            conn.commit()
            response = jsonify({"msg": "Account updated successfully!"}), 200
        else:
            response = jsonify({"msg": "Current password is incorrect"}), 400

    except Exception as e:
        print(e)  # Log the error for debugging
        response = jsonify({"msg": "An error occurred"}), 400

    finally:
        cursor.close()
        conn.close()

    return response


@app.route('/api/deleteAccount', methods=['DELETE'])
@jwt_required()
def delete_account():
    username = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM ScheduleClasses WHERE scheduleId IN (SELECT scheduleid FROM Schedules WHERE username = %s)",
            (username,)
        )
        cursor.execute(
            "DELETE FROM Schedules WHERE username = %s",
            (username,)
        )

        cursor.execute("DELETE FROM users WHERE username = (%s)", (username,))
        conn.commit()
        response = jsonify({"msg": "Account deleted successfully!"}), 200
        return response

    except Exception as e:
        conn.rollback()
        return jsonify({"msg": str(e)}), 400
    finally:
        cursor.close()
        conn.close()


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

@app.route('/api/reqClasses', methods=['GET'])
def req_classes():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT course_name, AVG(difficulty) AS average_difficulty, (SELECT hours FROM ( SELECT hours, COUNT(*) AS hour_count FROM ratings WHERE course_name = t.course_name GROUP BY hours ORDER BY hour_count DESC LIMIT 1 ) AS subquery) AS most_common_hour, (SELECT grade FROM ( SELECT grade, COUNT(*) AS grade_count FROM ratings WHERE course_name = t.course_name GROUP BY grade ORDER BY grade_count DESC LIMIT 1 ) AS subquery) AS most_common_grade FROM ratings t GROUP BY course_name;")
        result = cursor.fetchall()
        if result:
            cursor.close()
            conn.close()
            return jsonify(result), 200
        else:
            return jsonify({"msg": "Classes not found"}), 404
    except:
        return jsonify({"msg": "Classes not found"}), 404


def find_entry_with_least_credits(task_status):
    min_credits = float('inf')
    semester_with_min_credits = None

    for semester, data in task_status.items():
        if semester == 'AP/Summer':
            continue
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
        cursor.execute("SELECT DISTINCT ConcentrationName FROM Classes WHERE ConcentrationName IS NOT NULL;")
        concentrations = cursor.fetchall()
        concentration_list = [{'id': 0, 'name': 'None'}]
        for index, concentration in enumerate(concentrations, start=1):
            concentration_list.append({'id': index, 'name': concentration[0]})

        return jsonify(concentration_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/updateConcentrations', methods=['POST'])
def update_concentrations():
    data = request.get_json()
    task_status = data.get('taskStatus')
    print(task_status)
    concentration_name = data.get('concentrationName')

    if not task_status or concentration_name is None:
        return jsonify({'error': 'Missing taskStatus or concentrationName'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Retrieve original CS curriculum classes
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM Classes WHERE Classification = 'Major'")
        cs_classes = cursor.fetchall()
        cs_class_dict = {str(class_id): {"content": class_name, "credits": credits, "isFixed": bool(is_fixed), "attribute": attribute, "type": "Major", 'minorName': None, 'concentrationName': None} for class_id, class_name, credits, semester, is_fixed, attribute in cs_classes}
        # Update task_status for items with type 'Concentration'
        for semester_name, semester_data in task_status.items():
            updated_items = []
            for item in semester_data['items']:
                if item.get('type') == 'Concentration':
                    if item['id'] in cs_class_dict:
                        # Create a new item based on cs_class_dict but preserve the original 'id'
                        new_item = cs_class_dict[item['id']].copy()  # Copy the item from cs_class_dict
                        new_item['id'] = item['id']  # Preserve the original 'id'
                        updated_items.append(new_item)
                # If the item id is not in cs_class_dict, it's not appended (effectively removed)
                else:
                    updated_items.append(item)  # Keep the item if it's not of 'Concentration' type

            # Replace the items in the semester with the updated list
            semester_data['items'] = updated_items

        # Handle the selected concentration
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute, CountsFor FROM Classes WHERE ConcentrationName = %s", (concentration_name,))
        concentration_classes = cursor.fetchall()

        # Find the current max_id in task_status
        max_id = max(int(item['id']) for semester_data in task_status.values() for item in semester_data['items'] if 'id' in item)

        if concentration_classes:
            for _, class_name, credits, semester, is_fixed, attribute, counts_for in concentration_classes:
                class_found = False

                # Check for an existing class in task_status with a matching 'content'
                if counts_for:
                    for cls in counts_for.split(','):
                        for semester_data in task_status.values():
                            for item in semester_data['items']:
                                if item['content'] == cls:
                                    # Replace the first instance found
                                    item.update({'id': item['id'], 'content': class_name, 'credits': credits, 'isFixed': bool(is_fixed), 'type': 'Concentration', 'minorName': None, 'concentrationName': concentration_name})
                                    class_found = True
                                    break
                            if class_found:
                                break
                        if class_found:
                            break

                # If the class was not found, add it to the semester with the least credits
                if not class_found:
                    max_id += 1
                    semester_with_least_credits = find_entry_with_least_credits(task_status)
                    task_status[semester_with_least_credits]['items'].append({
                        'id': str(max_id),
                        'content': class_name,
                        'credits': credits,
                        'isFixed': bool(is_fixed),
                        'attribute': attribute,
                        'type': 'Concentration',
                        'minor_name': None,
                        'concentrationName': concentration_name,
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
        cursor.execute("SELECT DISTINCT MinorName FROM Classes WHERE MinorName IS NOT NULL;")
        minors = cursor.fetchall()
        minor_list = [{'id': 0, 'name': 'None'}]
        for index, minor in enumerate(minors, start=1):
            minor_list.append({'id': index, 'name': minor[0]})

        return jsonify(minor_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/updateMinors', methods=['POST'])
def update_minors():
    data = request.get_json()
    task_status = data.get('taskStatus')
    minor_name = data.get('minorName')

    if not task_status or minor_name is None:
        return jsonify({'error': 'Missing taskStatus or minorName'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Retrieve original CS curriculum classes
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM Classes WHERE Classification = 'Major'")
        cs_classes = cursor.fetchall()
        cs_class_dict = {str(class_id): {"content": class_name, "credits": credits, "isFixed": bool(is_fixed), "attribute": attribute, "type": "Major", 'minorName': None, 'concentrationName': None} for class_id, class_name, credits, semester, is_fixed, attribute in cs_classes}
        # Update task_status for items with type 'Minor'
        for semester_name, semester_data in task_status.items():
            updated_items = []
            for item in semester_data['items']:
                if item.get('type') == 'Minor':
                    if item['id'] in cs_class_dict:
                        # Create a new item based on cs_class_dict but preserve the original 'id'
                        new_item = cs_class_dict[item['id']].copy()  # Copy the item from cs_class_dict
                        new_item['id'] = item['id']  # Preserve the original 'id'
                        updated_items.append(new_item)
                # If the item id is not in cs_class_dict, it's not appended (effectively removed)
                else:
                    updated_items.append(item)  # Keep the item if it's not of 'Concentration' type

            # Replace the items in the semester with the updated list
            semester_data['items'] = updated_items

        # Handle the selected concentration
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute, CountsFor FROM Classes WHERE MinorName = %s", (minor_name,))
        minor_classes = cursor.fetchall()

        # Find the current max_id in task_status
        max_id = max(int(item['id']) for semester_data in task_status.values() for item in semester_data['items'] if 'id' in item)

        if minor_classes:
            for _, class_name, credits, semester, is_fixed, attribute, counts_for in minor_classes:
                class_found = False

                # Check for an existing class in task_status with a matching 'content'
                if counts_for:
                    for cls in counts_for.split(','):
                        for semester_data in task_status.values():
                            for item in semester_data['items']:
                                if item['content'] == cls:
                                    # Replace the first instance found
                                    item.update({'id': item['id'], 'content': class_name, 'credits': credits, 'isFixed': bool(is_fixed), 'type': 'Minor', 'minorName': minor_name, 'concentrationName': None})
                                    class_found = True
                                    break
                            if class_found:
                                break
                        if class_found:
                            break

                # If the class was not found, add it to the semester with the least credits
                if not class_found:
                    max_id += 1
                    semester_with_least_credits = find_entry_with_least_credits(task_status)
                    task_status[semester_with_least_credits]['items'].append({
                        'id': str(max_id),
                        'content': class_name,
                        'credits': credits,
                        'isFixed': bool(is_fixed),
                        'attribute': attribute,
                        'type': 'Minor',
                        'minorName': minor_name,
                        'concentrationName': None,
                    })

        return jsonify(task_status), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/getScheduleNames', methods=['GET'])
@jwt_required()
def get_schedule_names():
    username = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT ScheduleName FROM Schedules WHERE Username = (%s);", (username,))
        schedule_names = cursor.fetchall()

        if not schedule_names:
            return jsonify([]), 200

        schedules_name_list = [name[0] for name in schedule_names]

        return jsonify(schedules_name_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/getSchedule', methods=['GET'])
@jwt_required()
def get_schedule():
    username = get_jwt_identity()
    schedule_name = request.args.get('scheduleName')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get ScheduleID
        cursor.execute("SELECT ScheduleID FROM Schedules WHERE ScheduleName = %s AND UserName = %s;", (schedule_name, username))
        schedule_id_row = cursor.fetchone()
        if schedule_id_row is None:
            return jsonify({"msg": "Schedule not found"}), 404

        schedule_id = schedule_id_row[0]

        # Get associated classes and semesters
        cursor.execute("SELECT ClassID, Semester, ClassName, MinorName, ConcentrationName FROM ScheduleClasses WHERE ScheduleID = %s;", (schedule_id,))
        schedule_classes = cursor.fetchall()

        task_status = {
            "Freshman Fall": {"name": "Freshman Fall", "items": []},
            "Freshman Spring": {"name": "Freshman Spring", "items": []},
            "Sophomore Fall": {"name": "Sophomore Fall", "items": []},
            "Sophomore Spring": {"name": "Sophomore Spring", "items": []},
            "Junior Fall": {"name": "Junior Fall", "items": []},
            "Junior Spring": {"name": "Junior Spring", "items": []},
            "Senior Fall": {"name": "Senior Fall", "items": []},
            "Senior Spring": {"name": "Senior Spring", "items": []},
            "AP/Summer": {"name": "AP/Summer", "items": []},
            "ScheduleName": schedule_name}

        for class_id, semester, class_name, minor_name, concentration_name in schedule_classes:
            # Fetch class details
            cursor.execute("SELECT Credits, IsFixed, Attribute, CountsFor FROM Classes WHERE ClassID = %s;", (class_id,))
            class_info = cursor.fetchone()

            if class_info:
                credits, is_fixed, attribute, counts_for = class_info

                if semester not in task_status:
                    task_status[semester] = {"name": semester, "items": []}

                classification = "Major"
                if minor_name:
                    classification = "Minor"
                elif concentration_name:
                    classification = "Concentration"

                # Append class info to the corresponding semester
                task_status[semester]["items"].append({
                    "id": str(class_id),
                    "content": class_name,
                    "credits": int(credits),
                    "isFixed": bool(is_fixed),
                    "attribute": attribute,
                    "type": classification,
                    "countsFor": counts_for,
                    "minorName": minor_name,
                    "concentrationName": concentration_name,
                })

        return jsonify(task_status), 200

    except Exception as e:
        return jsonify({"msg": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/api/createSchedule', methods=['POST'])
@jwt_required()
def create_schedule():
    username = get_jwt_identity()
    data = request.get_json()
    schedule_name = data.get('ScheduleName')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO Schedules (Username, ScheduleName) VALUES (%s, %s)", (username, schedule_name))
        schedule_id = cursor.lastrowid

        # Fetch major classes and prepare bulk insert data
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM Classes WHERE Classification='Major'")
        courses = cursor.fetchall()

        task_status = {
            "Freshman Fall": {"name": "Freshman Fall", "items": []},
            "Freshman Spring": {"name": "Freshman Spring", "items": []},
            "Sophomore Fall": {"name": "Sophomore Fall", "items": []},
            "Sophomore Spring": {"name": "Sophomore Spring", "items": []},
            "Junior Fall": {"name": "Junior Fall", "items": []},
            "Junior Spring": {"name": "Junior Spring", "items": []},
            "Senior Fall": {"name": "Senior Fall", "items": []},
            "Senior Spring": {"name": "Senior Spring", "items": []},
            "AP/Summer": {"name": "AP/Summer", "items": []},
            "ScheduleName": schedule_name}

        insert_values = []
        for course in courses:
            class_id, class_name, credits, semester, is_fixed, attribute = course
            if semester not in task_status:
                task_status[semester] = {"name": semester, "items": []}

            class_item = {
                "id": str(class_id),
                "content": class_name,
                "credits": int(credits),
                "isFixed": bool(is_fixed),
                "attribute": attribute,
                "type": "Major",
                "concentrationName": None,
                "minorName": None,
            }
            task_status[semester]["items"].append(class_item)

            insert_values.append((schedule_id, class_id, semester, class_name))

        cursor.executemany("INSERT INTO ScheduleClasses (ScheduleID, ClassID, Semester, ClassName) VALUES (%s, %s, %s, %s);", insert_values)

        conn.commit()
        return jsonify(task_status), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"msg": str(e)}), 500

    finally:
        cursor.close()


@app.route('/api/saveSchedule', methods=['PUT'])
@jwt_required()
def save_schedule():
    username = get_jwt_identity()
    data = request.get_json()
    schedule_name = data.get('ScheduleName')
    task_status = data.get('taskStatus')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT ScheduleID FROM Schedules WHERE ScheduleName = %s AND UserName = %s;", (schedule_name, username))
        schedule_id_row = cursor.fetchone()
        if schedule_id_row is None:
            raise ValueError("Schedule not found")

        schedule_id = schedule_id_row[0]

        # Delete existing schedule classes for this schedule_id
        cursor.execute("DELETE FROM ScheduleClasses WHERE ScheduleID = %s;", (schedule_id,))

        # Insert new schedule classes
        for semester, classes_info in task_status.items():
            for class_info in classes_info.get('items', []):
                class_id = class_info.get('id')
                class_name = class_info.get('content')
                minor_name = class_info.get('minorName')
                concentration_name = class_info.get('concentrationName')

                cursor.execute("INSERT INTO ScheduleClasses (ScheduleID, ClassID, Semester, ClassName, MinorName, ConcentrationName) VALUES (%s, %s, %s, %s, %s, %s);",
                               (schedule_id, class_id, semester, class_name, minor_name, concentration_name))

        conn.commit()
        return {"message": "Schedule saved successfully"}, 200

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}, 500

    finally:
        cursor.close()
        conn.close()


@app.route('/api/deleteSchedule', methods=['DELETE'])
@jwt_required()
def delete_schedule():
    username = get_jwt_identity()
    schedule_name = request.args.get('scheduleName')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get ScheduleID
        cursor.execute("SELECT ScheduleID FROM Schedules WHERE ScheduleName = %s AND UserName = %s;", (schedule_name, username))
        schedule_id_row = cursor.fetchone()
        if schedule_id_row is None:
            raise ValueError("Schedule not found")

        schedule_id = schedule_id_row[0]

        # Delete schedule classes associated with this schedule_id
        cursor.execute("DELETE FROM ScheduleClasses WHERE ScheduleID = %s;", (schedule_id,))

        # Delete the schedule itself
        cursor.execute("DELETE FROM Schedules WHERE ScheduleID = %s;", (schedule_id,))

        conn.commit()
        return {"message": "Schedule deleted successfully"}, 200

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}, 500

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
