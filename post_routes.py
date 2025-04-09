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