from flask import Blueprint, request, jsonify
from firebase_admin import auth
from firebase_init import initialize_firebase

# Initialize Firebase
initialize_firebase()

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Authenticate user with Firebase
        user = auth.get_user_by_email(email)
        
        # If no exception is raised, the user is valid
        return jsonify({
            'message': 'Login successful',
            'user': {
                'uid': user.uid,
                'email': user.email
            }
        }), 200

    except auth.UserNotFoundError:
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500