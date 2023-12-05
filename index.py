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


# @app.route('/api/csClasses', methods=['GET'])
# def cs_classes():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#
#     try:
#         cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM Classes WHERE Classification='Major'")
#         courses = cursor.fetchall()
#
#         course_dict = {"AP/Summer": {"name": "AP/Summer", "items": []}}
#         for course in courses:
#             class_id, class_name, credits, semester, is_fixed, attribute = course
#             if semester not in course_dict:
#                 course_dict[semester] = {
#                     "name": semester,
#                     "items": []
#                 }
#
#             course_dict[semester]["items"].append({
#                 "id": str(class_id),
#                 "content": class_name,
#                 "credits": int(credits),
#                 "isFixed": bool(is_fixed),
#                 "attribute": attribute,
#                 "type": "Major",
#             })
#
#         if course_dict:
#             return jsonify(course_dict), 200
#         else:
#             return jsonify({"msg": "No courses found"}), 404
#     except Exception as e:
#         return jsonify({"msg": str(e)}), 500
#     finally:
#         cursor.close()


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
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM Classes")
        cs_classes = cursor.fetchall()
        cs_class_dict = {str(class_id): {"content": class_name, "credits": credits, "isFixed": bool(is_fixed), "attribute": attribute, "type": "Major"} for class_id, class_name, credits, semester, is_fixed, attribute in cs_classes}
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
        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM ConcentrationClasses WHERE ConcentrationID = %s", (concentration_id,))
        concentration_classes = cursor.fetchall()

        # Find the current max_id in task_status
        max_id = max(int(item['id']) for semester_data in task_status.values() for item in semester_data['items'] if 'id' in item)

        if concentration_classes:
            for _, class_name, credits, semester, is_fixed, attribute in concentration_classes:
                class_found = False

                # Check for an existing class in task_status with a matching 'content'
                for semester_data in task_status.values():
                    for item in semester_data['items']:
                        if item['content'] == attribute:
                            # Replace the first instance found
                            item.update({'id': item['id'], 'content': class_name, 'credits': credits, 'isFixed': bool(is_fixed), 'type': 'Concentration'})
                            class_found = True
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
        cs_class_dict = {str(class_id): {"content": class_name, "credits": credits, "isFixed": bool(is_fixed), "attribute": attribute, "type": "Major"} for class_id, class_name, credits, semester, is_fixed, attribute in cs_classes}
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
                                    item.update({'id': item['id'], 'content': class_name, 'credits': credits, 'isFixed': bool(is_fixed), 'type': 'Minor'})
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


@app.route('/api/createSchedule', methods=['POST'])
@jwt_required()
def create_schedule():
    username = get_jwt_identity()
    data = request.get_json()
    schedule_name = data.get('ScheduleName')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT ScheduleName FROM Schedules WHERE Username = (%s);", (username,))
        schedule_names = cursor.fetchall()

        if schedule_names:
            schedules_name_list = [name[0] for name in schedule_names]
            if schedule_name in schedules_name_list:
                return jsonify({"error": "Schedule name must be unique"}), 500

        # insert username/schedule_name into database
        # cursor.execute("INSERT INTO Schedules (Username, ScheduleName) VALUES (%s, %s)", (username, schedule_name,))

        cursor.execute("SELECT ClassID, ClassName, Credits, Semester, IsFixed, Attribute FROM Classes WHERE Classification='Major'")
        courses = cursor.fetchall()

        course_dict = {"ScheduleName": schedule_name, "AP/Summer": {"name": "AP/Summer", "items": []}}
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
                "attribute": attribute,
                "type": "Major",
            })


        if course_dict:
            return jsonify(course_dict), 200
        else:
            return jsonify({"msg": "No courses found"}), 404
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

        for semester, classes_info in task_status.items():
            for class_info in classes_info.get('items', []):
                class_id = class_info.get('id')
                cursor.execute("INSERT INTO ScheduleClasses (ScheduleID, ClassID, Semester) VALUES (%s, %s, %s);",
                               (schedule_id, class_id, semester))

        conn.commit()
        return {"message": "Schedule saved successfully"}, 200

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}, 500

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
