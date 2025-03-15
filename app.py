import bcrypt
from dotenv import load_dotenv
import os
import jwt
load_dotenv()

# Import the 'Flask' class from the 'flask' library.
from flask import Flask, jsonify, request , g

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