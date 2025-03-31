import bcrypt
from dotenv import load_dotenv
import os
import jwt
load_dotenv()

# Import the 'Flask' class from the 'flask' library.
from flask import Flask, jsonify, request , g
from flask_cors import CORS 
from auth_middleware import token_required

import psycopg2, psycopg2.extras


# Initialize Flask
# We'll use the pre-defined global '__name__' variable to tell Flask where it is.
app = Flask(__name__)
CORS(app)

def get_db_connection():
    connection = psycopg2.connect(host='localhost',
                            database='anime_blog',
                            user=os.getenv('POSTGRES_USERNAME'),
                            password=os.getenv('POSTGRES_PASSWORD'))
    return connection


@app.route('/sign-token', methods=['GET'])
def sign_token():
    user = {
        "id": 1,
        "username": "sai",
        "email": "sai@email.com",
        "password": "kamara"
    }
    token = jwt.encode(user, os.getenv('JWT_SECRET'), algorithm="HS256")    
    return jsonify({"token": token})

@app.route('/verify-token', methods=['POST'])
def verify_token():
    try:
        token = request.headers.get('Authorization').split(' ')[1]
        decoded_token = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=["HS256"])
        return jsonify({"user": decoded_token})
    except Exception as error:
       return jsonify({"error": str(error)})
    

    @app.route('/auth/sign-up', methods=['POST'])
    def signup():
        try:
            new_user_data = request.get_json()
            connection = get_db_connection()
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM users Where username = %s or email = %s;", (new_user_data["username"], new_user_data["email"],))
            existing_user = cursor.fetchone()
            if existing_user:
                curosr.close()
                return jsonify({"error": "Username already taken"}), 400
            hashed_password = bcrypt.hashpw(bytes(new_user_data["password"], 'utf-8'), bcrypt.gensalt())
            cursor.excute("INSERT INTO users (username,email,password) VALUES(%s, %s, %s) RETURNING id,username", (new_user_data["username"], new_user_data["email"],hashed_password.decode('utf-8')))