from functools import wraps
from flask import request, jsonify, g
import jwt
import os

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        authorization_header = request.headers.get('Authorization')
        if authorization_header is None:
            return jsonify({"error": "Authorization header is missing"}), 401
        try:          
            token = authorization_header.split(' ')[1]
            token_data = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=["HS256"])
            g.user = token_data.get("payload") or token_data
            if g.user is None:
                return jsonify({"error": "Invalid token: 'payload' key not found"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except Exception as error:
            return jsonify({"error": f"An error occurred: {str(error)}"}), 500

        
        return f(*args, **kwargs)
    return decorated_function