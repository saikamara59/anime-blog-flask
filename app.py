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
    connection = psycopg2.connect(
        host='localhost',
        database='anime_blog',
        user=os.getenv('POSTGRES_USERNAME'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
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
        cursor.execute("SELECT * FROM users WHERE username = %s or email = %s;", (new_user_data["username"], new_user_data["email"],)) 
        existing_user = cursor.fetchone()
        if existing_user:
            cursor.close()
            return jsonify({"error": "Username already taken"}), 400
        hashed_password = bcrypt.hashpw(bytes(new_user_data["password"], 'utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username,email, password) VALUES (%s, %s, %s) RETURNING id,username", (new_user_data["username"], new_user_data["email"],hashed_password.decode('utf-8')))
        created_user = cursor.fetchone()
        connection.commit()
        cursor.close()
        connection.close()
        payload = {"username": created_user["username"], "id": created_user["id"]}
        token = jwt.encode({ "payload": payload }, os.getenv('JWT_SECRET'))
        return jsonify({"token": token, "user": created_user}), 201
    except Exception as err:
        return jsonify({"error":  str(err)}), 401
        
@app.route('/auth/sign-in', methods=["POST"])
def sign_in():
    try:
        sign_in_form_data = request.get_json()
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s;", (sign_in_form_data["username"],))
        existing_user = cursor.fetchone()
        if existing_user is None:
            return jsonify({"err": "Wrong Username/Password"}), 401
        password_is_valid = bcrypt.checkpw(bytes(
            sign_in_form_data["password"], 'utf-8'), bytes(existing_user["password"], 'utf-8'))
        if not password_is_valid:
            return jsonify({"error": "Invalid credentials."}), 401
        payload = {"username": existing_user["username"], "id": existing_user["id"]}
        token = jwt.encode({"payload": payload}, os.getenv('JWT_SECRET'))
        return jsonify({"token": token}), 200
    except Exception as err:
        return jsonify({"err": "Wrong Username/Password."}), 500
    finally: 
            connection.close()   

@app.route('/')
def index():
  return "Landing Page"            



@app.route('/posts', methods=['POST'])
@token_required
def create_post():
    try:
        # Get the current user from the global 'g' object
        current_user = g.user

        # Get the post data from the request
        post_data = request.get_json()
        
        # Validate required fields
        if not post_data.get("title"):
            return jsonify({"error": "Title is required"}), 400
        
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Insert the new post into the database
        cursor.execute(
            """
            INSERT INTO posts (title, content, tags, user_id, media_url) 
            VALUES (%s, %s, %s, %s, %s) RETURNING *;
            """,
            (
                post_data["title"],
                post_data.get("content"),  # Optional content
                post_data.get("tags"),    # Optional tags
                current_user["id"],       # User ID from the token
                post_data.get("media_url")  # Optional media URL
            )
        )
        
        # Fetch the newly created post
        new_post = cursor.fetchone()
        connection.commit()
        
        # Return the created post as a response
        return jsonify({"post": new_post}), 201
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()


@app.route('/posts', methods=['GET'])
def get_posts():
    try:
        # Get optional query parameters for filtering
        tag_filter = request.args.get('tag')  # Example: /posts?tag=anime

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Base query to fetch all posts
        query = """
            SELECT posts.*, users.username AS author 
            FROM posts 
            JOIN users ON posts.user_id = users.id
        """
        params = []

        # Add filtering by tag if provided
        if tag_filter:
            query += " WHERE tags ILIKE %s"
            params.append(f"%{tag_filter}%")

        # Execute the query
        cursor.execute(query, params)
        posts = cursor.fetchall()

        # Return the posts as a response
        return jsonify({"posts": posts}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()


@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query to fetch the post by ID
        query = """
            SELECT posts.*, users.username AS author 
            FROM posts 
            JOIN users ON posts.user_id = users.id
            WHERE posts.id = %s
        """
        cursor.execute(query, (post_id,))
        post = cursor.fetchone()

        # If the post is not found, return a 404 error
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Return the post as a response
        return jsonify({"post": post}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()