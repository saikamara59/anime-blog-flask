from flask import Blueprint, jsonify, request, g
from auth_middleware import token_required
from db_utils import get_db_connection  # Import from db_utils.py
import psycopg2.extras


post_routes = Blueprint('post_routes', __name__)


@post_routes.route('/posts', methods=['POST'])
@token_required
def create_post():
    try:
        current_user = g.user
        post_data = request.get_json()
        if not post_data.get("title"):
            return jsonify({"error": "Title is required"}), 400
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            INSERT INTO posts (title, content, tags, user_id, media_url) 
            VALUES (%s, %s, %s, %s, %s) RETURNING *;
            """,
            (
                post_data["title"],
                post_data.get("content"),
                post_data.get("tags"),
                current_user["id"],
                post_data.get("media_url")
            )
        )
        new_post = cursor.fetchone()
        connection.commit()
        return jsonify({"post": new_post}), 201
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()



@post_routes.route('/posts', methods=['GET'])
def get_posts():
    try:
        tag_filter = request.args.get('tag')
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = """
            SELECT posts.*, users.username AS author 
            FROM posts 
            JOIN users ON posts.user_id = users.id
        """
        params = []
        if tag_filter:
            query += " WHERE tags ILIKE %s"
            params.append(f"%{tag_filter}%")
        cursor.execute(query, params)
        posts = cursor.fetchall()
        return jsonify({"posts": posts}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = """
            SELECT posts.*, users.username AS author 
            FROM posts 
            JOIN users ON posts.user_id = users.id
            WHERE posts.id = %s
        """
        cursor.execute(query, (post_id,))
        post = cursor.fetchone()
        if not post:
            return jsonify({"error": "Post not found"}), 404
        return jsonify({"post": post}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()


@post_routes.route('/posts/<int:post_id>', methods=['PUT'])
@token_required
def update_post(post_id):
    try:
        current_user = g.user
        post_data = request.get_json()
        if not post_data.get("title") and not post_data.get("content") and not post_data.get("tags") and not post_data.get("media_url"):
            return jsonify({"error": "At least one field (title, content, tags, media_url) is required to update"}), 400
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM posts WHERE id = %s AND user_id = %s;", (post_id, current_user["id"]))
        post = cursor.fetchone()
        if not post:
            return jsonify({"error": "Post not found or you are not authorized to update this post"}), 403
        update_fields = []
        update_values = []
        if post_data.get("title"):
            update_fields.append("title = %s")
            update_values.append(post_data["title"])
        if post_data.get("content"):
            update_fields.append("content = %s")
            update_values.append(post_data["content"])
        if post_data.get("tags"):
            update_fields.append("tags = %s")
            update_values.append(post_data["tags"])
        if post_data.get("media_url"):
            update_fields.append("media_url = %s")
            update_values.append(post_data["media_url"])
        update_values.append(post_id)
        query = f"UPDATE posts SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING *;"
        cursor.execute(query, update_values)
        updated_post = cursor.fetchone()
        connection.commit()
        return jsonify({"post": updated_post}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()


@post_routes.route('/posts/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(post_id):
    try:
        # Get the current user from the global 'g' object
        current_user = g.user

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the post exists and belongs to the current user
        cursor.execute("SELECT * FROM posts WHERE id = %s AND user_id = %s;", (post_id, current_user["id"]))
        post = cursor.fetchone()

        if not post:
            return jsonify({"error": "Post not found or you are not authorized to delete this post"}), 403

        # Delete the post
        cursor.execute("DELETE FROM posts WHERE id = %s;", (post_id,))
        connection.commit()

        # Return a success message
        return jsonify({"message": "Post deleted successfully"}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()


@post_routes.route('/posts/<int:post_id>/comments', methods=['POST'])
@token_required
def add_comment(post_id):
    try:
        # Get the current user from the global 'g' object
        current_user = g.user

        # Get the comment data from the request
        comment_data = request.get_json()
        if not comment_data.get("content"):
            return jsonify({"error": "Comment content is required"}), 400

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the post exists
        cursor.execute("SELECT * FROM posts WHERE id = %s;", (post_id,))
        post = cursor.fetchone()
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Insert the comment into the database
        cursor.execute(
            """
            INSERT INTO comments (content, user_id, post_id) 
            VALUES (%s, %s, %s) RETURNING *;
            """,
            (comment_data["content"], current_user["id"], post_id)
        )
        new_comment = cursor.fetchone()
        connection.commit()

        # Return the created comment as a response
        return jsonify({"comment": new_comment}), 201
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the post exists
        cursor.execute("SELECT * FROM posts WHERE id = %s;", (post_id,))
        post = cursor.fetchone()
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Retrieve all comments for the post
        cursor.execute(
            """
            SELECT comments.*, users.username AS author 
            FROM comments 
            JOIN users ON comments.user_id = users.id
            WHERE comments.post_id = %s
            ORDER BY comments.created_at ASC;
            """,
            (post_id,)
        )
        comments = cursor.fetchall()

        # Return the comments as a response
        return jsonify({"comments": comments}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/comments/<int:comment_id>', methods=['DELETE'])
@token_required
def delete_comment(comment_id):
    try:
        # Get the current user from the global 'g' object
        current_user = g.user

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the comment exists and belongs to the current user
        cursor.execute("SELECT * FROM comments WHERE id = %s;", (comment_id,))
        comment = cursor.fetchone()

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        # Check if the user is authorized to delete the comment
        if comment["user_id"] != current_user["id"] and not current_user.get("is_admin"):
           return jsonify({"error": "You are not authorized to delete this comment"}), 403

        # Delete the comment
        cursor.execute("DELETE FROM comments WHERE id = %s;", (comment_id,))
        connection.commit()

        # Return a success message
        return jsonify({"message": "Comment deleted successfully"}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/posts/<int:post_id>/like', methods=['POST'])
@token_required
def like_post(post_id):
    try:
        # Get the current user from the global 'g' object
        current_user = g.user

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the post exists
        cursor.execute("SELECT * FROM posts WHERE id = %s;", (post_id,))
        post = cursor.fetchone()
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Check if the user has already liked the post
        cursor.execute("SELECT * FROM likes WHERE user_id = %s AND post_id = %s;", (current_user["id"], post_id))
        like = cursor.fetchone()
        if like:
            return jsonify({"error": "You have already liked this post"}), 400

        # Insert the like into the database
        cursor.execute(
            "INSERT INTO likes (user_id, post_id) VALUES (%s, %s) RETURNING *;",
            (current_user["id"], post_id)
        )
        new_like = cursor.fetchone()
        connection.commit()

        # Return a success message
        return jsonify({"message": "Post liked successfully", "like": new_like}), 201
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/posts/<int:post_id>/like', methods=['DELETE'])
@token_required
def unlike_post(post_id):
    try:
        # Get the current user from the global 'g' object
        current_user = g.user

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the like exists
        cursor.execute("SELECT * FROM likes WHERE user_id = %s AND post_id = %s;", (current_user["id"], post_id))
        like = cursor.fetchone()
        if not like:
            return jsonify({"error": "You have not liked this post"}), 400

        # Delete the like
        cursor.execute("DELETE FROM likes WHERE user_id = %s AND post_id = %s;", (current_user["id"], post_id))
        connection.commit()

        # Return a success message
        return jsonify({"message": "Post unliked successfully"}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/posts/<int:post_id>/likes', methods=['GET'])
def get_like_count(post_id):
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the post exists
        cursor.execute("SELECT * FROM posts WHERE id = %s;", (post_id,))
        post = cursor.fetchone()
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Get the like count for the post
        cursor.execute("SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s;", (post_id,))
        like_count = cursor.fetchone()

        # Return the like count
        return jsonify({"like_count": like_count["like_count"]}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Fetch the user's profile
        cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = %s;", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Return the user's profile
        return jsonify({"user": user}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user_profile(user_id):
    try:
        # Get the current user from the global 'g' object
        current_user = g.user

        # Ensure the user is updating their own profile
        if current_user["id"] != user_id:
            return jsonify({"error": "You are not authorized to update this profile"}), 403

        # Get the updated profile data from the request
        profile_data = request.get_json()
        if not profile_data:
            return jsonify({"error": "No data provided"}), 400

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Update the user's profile
        update_fields = []
        update_values = []

        if profile_data.get("username"):
            update_fields.append("username = %s")
            update_values.append(profile_data["username"])
        if profile_data.get("email"):
            update_fields.append("email = %s")
            update_values.append(profile_data["email"])

        if not update_fields:
            return jsonify({"error": "No valid fields to update"}), 400

        update_values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s RETURNING id, username, email, created_at;"
        cursor.execute(query, update_values)
        updated_user = cursor.fetchone()
        connection.commit()

        # Return the updated profile
        return jsonify({"user": updated_user}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()

@post_routes.route('/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if the user exists
        cursor.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Fetch all posts created by the user
        cursor.execute(
            """
            SELECT posts.*, users.username AS author 
            FROM posts 
            JOIN users ON posts.user_id = users.id
            WHERE posts.user_id = %s
            ORDER BY posts.created_at DESC;
            """,
            (user_id,)
        )
        posts = cursor.fetchall()

        # Return the user's posts
        return jsonify({"posts": posts}), 200
    except Exception as err:
        return jsonify({"error": str(err)}), 500
    finally:
        connection.close()